import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../l10n/app_localizations.dart';
import '../../core/models.dart';
import '../../core/state.dart';
import '../../core/repository.dart';
import '../../core/widgets.dart';
import '../../core/formatters.dart';
import '../../core/theme.dart';

List<Article> demoArticles(AppLocalizations s) => [
  Article(id: 'demo-1', title: s.newsTitle1, summary: s.newsSummary1,
    url: 'https://bitcoin.org/fa/', publisher: s.demoPublisher, publishedAt: DateTime.utc(2026, 10, 5, 7),
    coinIds: [1], demo: true, translated: false),
  Article(id: 'demo-2', title: s.newsTitle2, summary: s.newsSummary2,
    url: 'https://coinmarketcap.com/academy', publisher: s.demoPublisher, publishedAt: DateTime.utc(2026, 10, 5, 6),
    coinIds: [1027], demo: true, translated: false)];

class NewsCard extends ConsumerWidget {
  const NewsCard(this.article, {super.key});
  final Article article;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = AppLocalizations.of(context), p = ref.watch(appStateProvider), a = article;
    return Card(child: Padding(padding: const EdgeInsets.all(Tokens.gutter), child: Column(
      crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (a.demo) Text(s.demoNews),
        Text(a.title.isEmpty ? s.pendingTranslation : a.title, style: Theme.of(context).textTheme.titleLarge),
        if (a.summary.isNotEmpty) Text(a.summary),
        Text('${a.publisher} · ${relativeTime(a.publishedAt, s, p.persian)}'),
        Text(tehranDate(a.publishedAt, p.persian)),
        if (a.translated) Text(s.machineTranslation),
        Wrap(spacing: Tokens.gap, children: [
          TextButton(onPressed: () => context.push('/news/${a.id}'), child: Text(s.openNews)),
          IconButton(tooltip: p.saved.contains(a.id) ? s.unsave : s.save,
            onPressed: () => ref.read(appStateProvider.notifier).toggleArticle(a.id),
            icon: Icon(p.saved.contains(a.id) ? Icons.bookmark : Icons.bookmark_outline))])])));
  }
}

class NewsPage extends ConsumerStatefulWidget {
  const NewsPage({super.key, this.coinId});
  final int? coinId;
  @override
  ConsumerState<NewsPage> createState() => _NewsPageState();
}
class _NewsPageState extends ConsumerState<NewsPage> {
  bool savedOnly = false, loadingMore = false, moreError = false, loadedMore = false;
  final List<Article> extra = [];
  int requestGeneration = 0;
  String? nextCursor;
  Resource<NewsBatch>? lastPage;
  Future<void> loadMore(String cursor) async {
    if (loadingMore) return;
    final generation = requestGeneration;
    setState(() { loadingMore = true; moreError = false; });
    try {
      final page = await ref.read(repositoryProvider).news(coinId: widget.coinId, cursor: cursor);
      if (!mounted || generation != requestGeneration) return;
      setState(() {
        extra.addAll(page.data.articles);
        nextCursor = page.data.nextCursor;
        lastPage = page;
        loadedMore = true;
      });
    } catch (_) { if (mounted && generation == requestGeneration) setState(() => moreError = true); }
    finally { if (mounted && generation == requestGeneration) setState(() => loadingMore = false); }
  }
  Future<void> refresh() async {
    setState(() { requestGeneration++; loadingMore = false; extra.clear(); loadedMore = false; nextCursor = null; lastPage = null; moreError = false; });
    if (ref.read(repositoryProvider).isDemo) return;
    try {
      if (savedOnly) {
        ref.invalidate(savedNewsProvider);
        await ref.read(savedNewsProvider.future);
      } else {
        ref.invalidate(newsProvider(widget.coinId));
        await ref.read(newsProvider(widget.coinId).future);
      }
    } catch (_) {
      // The provider exposes its error through RetryView; end the refresh indicator.
    }
  }
  @override
  Widget build(BuildContext context) {
    final s = AppLocalizations.of(context), p = ref.watch(appStateProvider);
    Widget list(List<Article> articles, {Resource<NewsBatch>? status, List<Resource<Article>> saved = const []}) {
      final unique = {for (final a in articles) a.id: a}.values.where((a) =>
        (!savedOnly || p.saved.contains(a.id)) && (widget.coinId == null || a.coinIds.contains(widget.coinId))).toList();
      final cursor = loadedMore ? nextCursor : status?.data.nextCursor;
      return RefreshIndicator(onRefresh: refresh, child: CustomScrollView(
        key: PageStorageKey('news:${widget.coinId}:$savedOnly'), physics: const AlwaysScrollableScrollPhysics(),
        slivers: [SliverPadding(padding: const EdgeInsets.all(Tokens.gutter),
          sliver: SliverList.list(children: [
          if (status != null && status.unavailable) Text(s.newsUnavailable),
          if (status != null && !status.unavailable) DataStatus(fetchedAt: status.fetchedAt, persian: p.persian,
            offline: status.offline, stale: status.stale, demo: status.demo),
          if (lastPage != null && lastPage!.offline) Text(s.offline),
          if (lastPage != null && lastPage!.stale) Text(s.stale),
          if (saved.any((a) => a.offline)) Text(s.offline),
          if (saved.any((a) => a.stale)) Text(s.stale),
          SwitchListTile(title: Text(s.savedOnly), value: savedOnly, onChanged: (v) => setState(() => savedOnly = v)),
          if (unique.isEmpty) Text(s.empty),
          ])),
          SliverPadding(padding: const EdgeInsets.symmetric(horizontal: Tokens.gutter),
            sliver: SliverList.builder(itemCount: unique.length,
              itemBuilder: (context, index) => NewsCard(unique[index], key: ValueKey(unique[index].id)))),
          SliverPadding(padding: const EdgeInsets.all(Tokens.gutter), sliver: SliverList.list(children: [
          if (!savedOnly && cursor != null) ...[
            if (moreError) Text(s.networkError),
            FilledButton(onPressed: loadingMore ? null : () => loadMore(cursor),
              child: loadingMore ? const CircularProgressIndicator() : Text(moreError ? s.retry : s.loadMore))]]))]));
    }
    if (ref.watch(repositoryProvider).isDemo) return list(demoArticles(s), status: Resource(const NewsBatch([], null),
      fetchedAt: DateTime.utc(2026, 10, 5, 8), demo: true));
    if (savedOnly) return ref.watch(savedNewsProvider).when(
      data: (saved) => list(saved.map((r) => r.data).toList(), saved: saved),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, st) => Column(children: [
        SwitchListTile(title: Text(s.savedOnly), value: savedOnly, onChanged: (v) => setState(() => savedOnly = v)),
        Expanded(child: RetryView(retry: () => ref.invalidate(savedNewsProvider)))]));
    return ref.watch(newsProvider(widget.coinId)).when(
      data: (page) => list([...page.data.articles, ...extra], status: page),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, st) => RetryView(retry: () => ref.invalidate(newsProvider(widget.coinId))));
  }
}

class NewsDetailPage extends ConsumerWidget {
  const NewsDetailPage(this.id, {super.key});
  final String id;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = AppLocalizations.of(context), p = ref.watch(appStateProvider);
    Widget detail(Resource<Article> resource) {
      final a = resource.data;
      return ListView(padding: const EdgeInsets.all(Tokens.section), children: [
        DataStatus(fetchedAt: resource.fetchedAt, persian: p.persian,
          demo: resource.demo, offline: resource.offline, stale: resource.stale),
        if (a.demo) Text(s.demoNews),
        Text(a.title.isEmpty ? s.pendingTranslation : a.title, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: Tokens.gutter), if (a.summary.isNotEmpty) Text(a.summary),
        Text('${a.publisher} · ${relativeTime(a.publishedAt, s, p.persian)}'),
        Text(tehranDate(a.publishedAt, p.persian)),
        if (a.translated) Text(s.machineTranslation),
        const SizedBox(height: Tokens.gutter),
        FilledButton.icon(icon: const Icon(Icons.open_in_new), label: Text(s.source), onPressed: () async {
          final uri = Uri.tryParse(a.url);
          bool opened = false;
          try { if (uri != null && uri.scheme == 'https') opened = await launchUrl(uri, mode: LaunchMode.externalApplication); }
          catch (_) { opened = false; }
          if (!opened && context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s.linkError)));
        }),
        TextButton.icon(icon: const Icon(Icons.share_outlined), label: Text(s.share), onPressed: () async {
          try { await SharePlus.instance.share(ShareParams(text: a.url)); }
          catch (_) { if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s.shareError))); }
        }),
        TextButton.icon(icon: Icon(p.saved.contains(a.id) ? Icons.bookmark : Icons.bookmark_outline),
          label: Text(p.saved.contains(a.id) ? s.unsave : s.save),
          onPressed: () => ref.read(appStateProvider.notifier).toggleArticle(a.id))]);
    }
    Widget body;
    if (ref.watch(repositoryProvider).isDemo) {
      final matches = demoArticles(s).where((a) => a.id == id);
      body = matches.isEmpty ? Center(child: Text(s.empty)) : detail(Resource(matches.first,
        fetchedAt: DateTime.utc(2026, 10, 5, 8), demo: true));
    } else {
      body = ref.watch(articleProvider(id)).when(data: detail,
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, st) => RetryView(retry: () => ref.invalidate(articleProvider(id))));
    }
    return Scaffold(appBar: AppBar(title: Text(s.news)), body: SafeArea(child: body));
  }
}
