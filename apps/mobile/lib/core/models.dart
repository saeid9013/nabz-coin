class Coin {
  const Coin({required this.id, required this.rank, required this.name,
    required this.symbol, required this.price, required this.change,
    required this.volume, required this.marketCap, this.logoUrl});
  final int id, rank;
  final String name, symbol;
  final double price, change, volume, marketCap;
  final String? logoUrl;
  factory Coin.fromJson(Map<String, dynamic> j) => Coin(
    id: j['id'] as int, rank: j['rank'] as int, name: j['name'] as String,
    symbol: j['symbol'] as String, price: (j['price'] as num).toDouble(),
    change: (j['change_24h'] as num).toDouble(),
    volume: (j['volume_24h'] as num).toDouble(), marketCap: (j['market_cap'] as num).toDouble(),
    logoUrl: j['logo_url'] as String?);
}

class Article {
  const Article({required this.id, required this.title, required this.summary,
    required this.url, required this.publisher, required this.publishedAt,
    required this.coinIds, required this.demo, required this.translated});
  final String id, title, summary, url, publisher;
  final DateTime publishedAt;
  final List<int> coinIds;
  final bool demo, translated;
  factory Article.fromJson(Map<String, dynamic> j) => Article(
    id: j['id'] as String, title: j['title_fa'] as String? ?? '',
    summary: j['summary_fa'] as String? ?? '', url: j['url'] as String,
    publisher: j['publisher'] as String, publishedAt: DateTime.parse(j['published_at'] as String),
    coinIds: (j['coin_ids'] as List).cast<int>(), demo: j['demo'] as bool,
    translated: j['translation_status'] == 'ready');
}

class MarketSnapshot {
  MarketSnapshot(this.coins, this.fetchedAt, {this.offline = false, this.demo = false});
  final List<Coin> coins;
  final DateTime fetchedAt;
  final bool offline, demo;
  bool get stale => DateTime.now().toUtc().difference(fetchedAt).inMinutes >= 20;
}

class ChartPoint {
  ChartPoint(this.time, this.price);
  final DateTime time;
  final double price;
}

class Resource<T> {
  const Resource(this.data, {required this.fetchedAt, this.offline = false,
    this.demo = false, this.unavailable = false, this.maxAgeMinutes = 20, this.source});
  final T data;
  final DateTime fetchedAt;
  final bool offline, demo, unavailable;
  final int maxAgeMinutes;
  final String? source;
  bool get stale => !demo && DateTime.now().toUtc().difference(fetchedAt).inMinutes >= maxAgeMinutes;
}

class NewsBatch {
  const NewsBatch(this.articles, this.nextCursor);
  final List<Article> articles;
  final String? nextCursor;
}

class Overview {
  const Overview({required this.marketCap, required this.volume, required this.btcDominance});
  final double? marketCap, volume, btcDominance;
  factory Overview.fromJson(Map<String, dynamic> j) {
    final quote = ((j['quote'] as Map?)?['USD'] as Map?) ?? j;
    return Overview(marketCap: (quote['total_market_cap'] as num?)?.toDouble(),
      volume: (quote['total_volume_24h'] as num?)?.toDouble(),
      btcDominance: (j['btc_dominance'] as num?)?.toDouble());
  }
}
