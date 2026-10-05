import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:nabz_coin/core/repository.dart';

void main() {
  Future<SharedPreferences> preferences() async {
    SharedPreferences.setMockInitialValues({});
    return SharedPreferences.getInstance();
  }
  Map<String, dynamic> coin() => {'id': 1, 'rank': 1, 'name': 'Bitcoin', 'symbol': 'BTC',
    'price': 62000.25, 'change_24h': -2.4, 'volume_24h': 100.0, 'market_cap': 1000.0};
  Map<String, dynamic> article() => {'id': 'a', 'title_fa': 'خبر نمونه آزمون', 'summary_fa': '',
    'url': 'https://example.com/article', 'publisher': 'Fixture', 'published_at': '2026-10-05T07:00:00Z',
    'coin_ids': [1], 'demo': false, 'translation_status': 'ready'};

  test('Market survives repository restart offline; client refuses demo and 403', () async {
    final prefs = await preferences();
    final dio = Dio(BaseOptions(baseUrl: 'https://api.example.com'));
    String mode = 'online';
    dio.interceptors.add(InterceptorsWrapper(onRequest: (options, handler) {
      if (mode == 'offline') return handler.reject(DioException(requestOptions: options, type: DioExceptionType.connectionError));
      if (mode == 'denied') return handler.reject(DioException(requestOptions: options, type: DioExceptionType.badResponse,
        response: Response(requestOptions: options, statusCode: 403)));
      handler.resolve(Response(requestOptions: options, data: {'mode': mode == 'demo' ? 'demo' : 'live',
        'fetched_at': '2020-01-01T00:00:00Z', 'items': [coin()]}));
    }));
    Repository make() => Repository(prefs, client: dio, demo: false, baseUrl: 'https://api.example.com');
    expect((await make().market()).coins.single.id, 1);
    mode = 'offline';
    final cached = await make().market();
    expect(cached.offline, isTrue);
    expect(cached.stale, isTrue);
    mode = 'denied';
    await expectLater(make().market(), throwsA(isA<DioException>()));
    mode = 'demo';
    await expectLater(make().market(), throwsStateError);
  });

  test('News page caches independent details and pagination; chart exposes stale offline status', () async {
    final prefs = await preferences();
    final dio = Dio(BaseOptions(baseUrl: 'https://api.example.com'));
    bool online = true;
    dio.interceptors.add(InterceptorsWrapper(onRequest: (options, handler) {
      if (!online) return handler.reject(DioException(requestOptions: options, type: DioExceptionType.connectionError));
      final data = options.path.endsWith('/chart')
        ? {'mode': 'live', 'fetched_at': '2020-01-01T00:00:00Z', 'source': 'collected', 'points': [
            {'time': '2020-01-01T00:01:00Z', 'price': 20}, {'time': '2020-01-01T00:00:00Z', 'price': 10}]}
        : {'mode': 'live', 'fetched_at': '2020-01-01T00:00:00Z', 'items': [article()], 'next_cursor': 'a'};
      handler.resolve(Response(requestOptions: options, data: data));
    }));
    final repository = Repository(prefs, client: dio, demo: false, baseUrl: 'https://api.example.com');
    final first = await repository.news(coinId: 1);
    expect(first.data.nextCursor, 'a');
    expect(first.stale, isTrue);
    await repository.chart(1, '7d');
    online = false;
    final saved = await repository.article('a');
    expect(saved.offline, isTrue);
    expect(saved.data.title, 'خبر نمونه آزمون');
    final chart = await repository.chart(1, '7d');
    expect(chart.offline, isTrue);
    expect(chart.stale, isTrue);
    expect(chart.data.first.price, 10);
    expect(chart.data.last.price, 20);
    expect((await repository.news(coinId: 1)).offline, isTrue);
  });

  test('Different API origins cannot reuse cache', () async {
    final prefs = await preferences();
    final dio = Dio(BaseOptions(baseUrl: 'https://second.example.com'));
    dio.interceptors.add(InterceptorsWrapper(onRequest: (o, h) => h.reject(DioException(requestOptions: o,
      type: DioExceptionType.connectionError))));
    await prefs.setString('market:https://first.example.com', '{}');
    final repo = Repository(prefs, client: dio, demo: false, baseUrl: 'https://second.example.com');
    await expectLater(repo.market(), throwsA(isA<DioException>()));
  });
}
