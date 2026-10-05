import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../l10n/app_localizations.dart';
import '../../core/repository.dart';
import '../../core/state.dart';
import '../../core/widgets.dart';
import '../../core/formatters.dart';
import '../../core/theme.dart';

class MarketPage extends ConsumerStatefulWidget {
  const MarketPage({super.key, this.watchOnly = false});
  final bool watchOnly;
  @override
  ConsumerState<MarketPage> createState() => _MarketPageState();
}
class _MarketPageState extends ConsumerState<MarketPage> {
  String query = '', sort = 'rank';
  @override
  Widget build(BuildContext context) {
    final s = AppLocalizations.of(context), p = ref.watch(appStateProvider);
    return ref.watch(marketProvider).when(loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, st) => RetryView(retry: () => ref.invalidate(marketProvider)), data: (snapshot) {
        final coins = snapshot.coins.where((c) => (!widget.watchOnly || p.watch.contains(c.id)) &&
          '${c.name} ${c.symbol}'.toLowerCase().contains(query.toLowerCase())).toList();
        coins.sort((a, b) => sort == 'gainers' ? b.change.compareTo(a.change)
          : sort == 'losers' ? a.change.compareTo(b.change) : a.rank.compareTo(b.rank));
        return RefreshIndicator(onRefresh: () async { ref.invalidate(marketProvider); await ref.read(marketProvider.future); },
          child: CustomScrollView(key: PageStorageKey(widget.watchOnly), slivers: [
            SliverPadding(padding: const EdgeInsets.all(Tokens.gutter), sliver: SliverToBoxAdapter(child: Column(
              crossAxisAlignment: CrossAxisAlignment.start, children: [
                DataStatus(fetchedAt: snapshot.fetchedAt, persian: p.persian, demo: snapshot.demo,
                  offline: snapshot.offline, stale: snapshot.stale),
                if (!widget.watchOnly) ref.watch(overviewProvider).when(
                  loading: () => const LinearProgressIndicator(),
                  error: (e, st) => TextButton(onPressed: () => ref.invalidate(overviewProvider), child: Text('${s.overview} · ${s.retry}')),
                  data: (overview) => Card(child: Padding(padding: const EdgeInsets.all(Tokens.gutter), child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(s.overview, style: Theme.of(context).textTheme.titleLarge),
                      DataStatus(fetchedAt: overview.fetchedAt, persian: p.persian, demo: overview.demo,
                        offline: overview.offline, stale: overview.stale),
                      if (overview.data.marketCap != null) ...[Text(s.marketCap), NumericText(usd(overview.data.marketCap!, p.persian))],
                      if (overview.data.volume != null) ...[Text(s.volume), NumericText(usd(overview.data.volume!, p.persian))],
                      if (overview.data.btcDominance != null) ...[Text(s.btcDominance),
                        NumericText('${digits(overview.data.btcDominance!.toStringAsFixed(1), p.persian)}%')]])))),
                const SizedBox(height: Tokens.gutter),
                TextField(decoration: InputDecoration(labelText: snapshot.demo ? s.search : s.searchLive, prefixIcon: const Icon(Icons.search)),
                  onChanged: (v) => setState(() => query = v)),
                const SizedBox(height: Tokens.gutter),
                DropdownButton<String>(isExpanded: true, value: sort, items: [
                  DropdownMenuItem(value: 'rank', child: Text(s.rank)),
                  DropdownMenuItem(value: 'gainers', child: Text(s.gainers)),
                  DropdownMenuItem(value: 'losers', child: Text(s.losers))],
                  onChanged: (v) => setState(() => sort = v!)),
                if (coins.isEmpty) Padding(padding: const EdgeInsets.all(Tokens.section),
                  child: Text(widget.watchOnly ? s.emptyWatch : s.empty))]))),
            SliverPadding(padding: const EdgeInsets.symmetric(horizontal: Tokens.gutter), sliver: SliverList.builder(
              itemCount: coins.length, itemBuilder: (c, i) => CoinTile(coins[i], onTap: () => context.push('/coin/${coins[i].id}'))))]));
      });
  }
}
