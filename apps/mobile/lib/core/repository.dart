import 'dart:convert';
import 'dart:math';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'models.dart';
import 'state.dart';

const demoMode = bool.fromEnvironment('DEMO_MODE', defaultValue: true);
const apiBaseUrl = String.fromEnvironment('API_BASE_URL');
final repositoryProvider = Provider<Repository>((ref) => Repository(ref.read(preferencesProvider)));
final marketProvider = FutureProvider<MarketSnapshot>((ref) => ref.read(repositoryProvider).market());
final newsProvider = FutureProvider.family<Resource<NewsBatch>, int?>((ref, coinId) => ref.read(repositoryProvider).news(coinId: coinId));
final articleProvider = FutureProvider.autoDispose.family<Resource<Article>, String>((ref, id) => ref.read(repositoryProvider).article(id));
final savedNewsProvider = FutureProvider<List<Resource<Article>>>((ref) async {
  final ids = ref.watch(appStateProvider.select((s) => s.saved)).toList()..sort();
  return Future.wait(ids.map(ref.read(repositoryProvider).article));
});
final overviewProvider = FutureProvider<Resource<Overview>>((ref) => ref.read(repositoryProvider).overview());
typedef ChartKey = ({int id, String range});
final chartProvider = FutureProvider.autoDispose.family<Resource<List<ChartPoint>>, ChartKey>(
  (ref, key) => ref.read(repositoryProvider).chart(key.id, key.range));

class Repository {
  Repository(this.storage, {Dio? client, bool? demo, String? baseUrl}) : isDemo = demo ?? demoMode,
    baseUrl = baseUrl ?? apiBaseUrl, dio = client ?? Dio(BaseOptions(baseUrl: baseUrl ?? apiBaseUrl,
    connectTimeout: const Duration(seconds: 8), receiveTimeout: const Duration(seconds: 12)));
  final SharedPreferences storage;
  final Dio dio;
  final bool isDemo;
  final String baseUrl;
  final demoTime = DateTime.utc(2026, 10, 5, 8);
  void requireLive() {
    final uri = Uri.tryParse(baseUrl);
    if (uri == null || !['http', 'https'].contains(uri.scheme) || uri.host.isEmpty) {
      throw StateError('API_BASE_URL must be configured in live mode');
    }
  }
  Future<MarketSnapshot> market() async {
    if (isDemo) return MarketSnapshot(demoCoins(), demoTime, demo: true);
    requireLive();
    Map<String, dynamic> body;
    bool offline = false;
    try {
      body = Map<String, dynamic>.from((await dio.get('/api/v1/market',
        queryParameters: {'limit': 100})).data as Map);
      if (body['mode'] != 'live') throw StateError('Live client refuses demo server');
      await storage.setString('market:$baseUrl', jsonEncode(body));
    } on DioException catch (e) {
      // Authentication/configuration/validation errors must not be hidden by fallback.
      if (e.response != null && (e.response!.statusCode ?? 500) < 500) rethrow;
      final cached = storage.getString('market:$baseUrl');
      if (cached == null) rethrow;
      body = Map<String, dynamic>.from(jsonDecode(cached) as Map);
      offline = true;
    }
    return MarketSnapshot((body['items'] as List).map((j) => Coin.fromJson(Map<String, dynamic>.from(j as Map))).toList(),
      DateTime.parse(body['fetched_at'] as String), offline: offline);
  }
  Future<Resource<NewsBatch>> news({int? coinId, String? cursor}) async {
    if (isDemo) return Resource(const NewsBatch([], null), fetchedAt: demoTime, demo: true);
    requireLive();
    final body = await cachedGet('/api/v1/news', {'limit': 20, if (coinId != null) 'coin_id': coinId,
      if (cursor != null) 'cursor': cursor});
    final raw = (body.data['items'] as List).map((j) => Map<String, dynamic>.from(j as Map)).toList();
    final articles = raw.map(Article.fromJson).toList();
    for (final item in raw) {
      await storage.setString('article:$baseUrl:${item['id']}', jsonEncode({
        ...item, 'mode': 'live', '_cached_at': body.data['_cached_at']}));
    }
    return Resource(NewsBatch(articles, body.data['next_cursor'] as String?), fetchedAt: cacheTime(body.data),
      offline: body.offline, maxAgeMinutes: 60, unavailable: body.data['freshness'] == 'unavailable');
  }
  Future<Resource<Article>> article(String id) async {
    requireLive();
    final key = 'article:$baseUrl:$id';
    try {
      final response = await dio.get('/api/v1/news/$id');
      final raw = Map<String, dynamic>.from(response.data as Map);
      if (raw['demo'] == true) throw StateError('Live client refuses demo article');
      final parsed = Article.fromJson(raw);
      final fetched = DateTime.now().toUtc();
      await storage.setString(key, jsonEncode({...raw, 'mode': 'live', '_cached_at': fetched.toIso8601String()}));
      return Resource(parsed, fetchedAt: fetched, maxAgeMinutes: 60);
    } on DioException catch (e) {
      if (e.response != null && (e.response!.statusCode ?? 500) < 500) rethrow;
      final previous = storage.getString(key);
      if (previous == null) rethrow;
      final raw = Map<String, dynamic>.from(jsonDecode(previous) as Map);
      return Resource(Article.fromJson(raw), fetchedAt: cacheTime(raw), offline: true, maxAgeMinutes: 60);
    }
  }
  Future<Resource<Overview>> overview() async {
    if (isDemo) return Resource(const Overview(marketCap: 2500000000000, volume: 89000000000, btcDominance: 54.2),
      fetchedAt: demoTime, demo: true, maxAgeMinutes: 60);
    final result = await cachedGet('/api/v1/market/overview', {});
    return Resource(Overview.fromJson(Map<String, dynamic>.from(result.data['data'] as Map)),
      fetchedAt: cacheTime(result.data), offline: result.offline, maxAgeMinutes: 60);
  }
  Future<Resource<List<ChartPoint>>> chart(int id, String range) async {
    if (isDemo) {
      final coin = demoCoins().firstWhere((c) => c.id == id);
      final days = {'1d': 1, '7d': 7, '30d': 30}[range]!;
      return Resource(List.generate(48, (i) => ChartPoint(demoTime.subtract(Duration(minutes: ((47 - i) * days * 1440 / 47).round())),
        coin.price * (0.97 + i / 1600 + sin(i * 0.5) * 0.008))), fetchedAt: demoTime, demo: true);
    }
    requireLive();
    final body = await cachedGet('/api/v1/coins/$id/chart', {'range': range});
    final points = (body.data['points'] as List).map((j) => ChartPoint(DateTime.parse(j['time'] as String),
      (j['price'] as num).toDouble())).toList();
    points.sort((a, b) => a.time.compareTo(b.time));
    return Resource(points, fetchedAt: cacheTime(body.data), offline: body.offline,
      unavailable: body.data['freshness'] == 'unavailable', source: body.data['source'] as String?);
  }
  DateTime cacheTime(Map<String, dynamic> body) => DateTime.parse(
    (body['fetched_at'] ?? body['_cached_at']) as String).toUtc();
  Future<({Map<String, dynamic> data, bool offline})> cachedGet(String path, Map<String, dynamic> params) async {
    requireLive();
    final key = '$baseUrl:$path:${jsonEncode(params)}';
    try {
      final data = Map<String, dynamic>.from((await dio.get(path, queryParameters: params)).data as Map);
      if (data['mode'] != 'live') throw StateError('Live client refuses demo server');
      data['_cached_at'] = DateTime.now().toUtc().toIso8601String();
      await storage.setString(key, jsonEncode(data));
      return (data: data, offline: false);
    } on DioException catch (e) {
      if (e.response != null && (e.response!.statusCode ?? 500) < 500) rethrow;
      final previous = storage.getString(key);
      if (previous == null) rethrow;
      return (data: Map<String, dynamic>.from(jsonDecode(previous) as Map), offline: true);
    }
  }
}

List<Coin> demoCoins() {
  const ids = [1, 1027, 825, 1839, 5426];
  const names = ['بیت‌کوین', 'اتریوم', 'تتر', 'بی‌ان‌بی', 'سولانا'];
  const symbols = ['BTC', 'ETH', 'USDT', 'BNB', 'SOL'];
  const prices = [62450.25, 2480.60, 1.0, 580.40, 145.12];
  return List.generate(100, (i) => Coin(id: i < 5 ? ids[i] : 900000 + i,
    rank: i + 1, name: i < 5 ? names[i] : 'کوین نمونه ${i + 1}',
    symbol: i < 5 ? symbols[i] : 'DEMO${i + 1}',
    price: i < 5 ? prices[i] : (i == 99 ? 0.0000000000123 : 1000 / (i + 1)),
    change: i.isEven ? 2.4 + i / 50 : -1.7 - i / 80,
    volume: 250000000 / (i + 1), marketCap: 1200000000 / (i + 1)));
}
