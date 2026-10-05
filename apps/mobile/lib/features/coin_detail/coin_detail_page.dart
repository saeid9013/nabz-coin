import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:go_router/go_router.dart';
import '../../l10n/app_localizations.dart';
import '../../core/repository.dart';
import '../../core/state.dart';
import '../../core/widgets.dart';
import '../../core/formatters.dart';
import '../../core/theme.dart';

class CoinDetailPage extends ConsumerStatefulWidget {
  const CoinDetailPage(this.id, {super.key});
  final int id;
  @override
  ConsumerState<CoinDetailPage> createState() => _CoinDetailPageState();
}
class _CoinDetailPageState extends ConsumerState<CoinDetailPage> {
  String range = '7d';
  bool showTable = false;
  @override
  Widget build(BuildContext context) {
    final s = AppLocalizations.of(context), p = ref.watch(appStateProvider);
    final key = (id: widget.id, range: range);
    return Scaffold(appBar: AppBar(title: Text(s.appName)), body: SafeArea(child: ref.watch(marketProvider).when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, st) => RetryView(retry: () => ref.invalidate(marketProvider)), data: (snapshot) {
        final matches = snapshot.coins.where((c) => c.id == widget.id);
        if (matches.isEmpty) return Center(child: Text(s.empty));
        final coin = matches.first;
        return ListView(padding: const EdgeInsets.all(Tokens.gutter), children: [
          if (snapshot.demo) Text(s.demo),
          CoinAvatar(coin),
          Text(coin.name, style: Theme.of(context).textTheme.headlineMedium),
          NumericText(coin.symbol), NumericText(usd(coin.price, p.persian), style: Theme.of(context).textTheme.headlineLarge),
          DataStatus(fetchedAt: snapshot.fetchedAt, persian: p.persian, offline: snapshot.offline, stale: snapshot.stale),
          TextButton.icon(onPressed: () => ref.read(appStateProvider.notifier).toggleCoin(coin.id),
            icon: Icon(p.watch.contains(coin.id) ? Icons.star : Icons.star_outline),
            label: Text(p.watch.contains(coin.id) ? s.removeWatch : s.addWatch)),
          const SizedBox(height: Tokens.section), Text(s.chart),
          Wrap(spacing: Tokens.gap, children: [for (final entry in {'1d': s.days1, '7d': s.days7, '30d': s.days30}.entries)
            ChoiceChip(label: Text(entry.value), selected: range == entry.key,
              onSelected: (_) => setState(() => range = entry.key))]),
          const SizedBox(height: Tokens.gutter),
          ref.watch(chartProvider(key)).when(loading: () => const SizedBox(height: 200, child: Center(child: CircularProgressIndicator())),
            error: (e, st) => RetryView(retry: () => ref.invalidate(chartProvider(key))), data: (resource) {
              final points = resource.data;
              if (points.isEmpty) return Column(children: [if (resource.offline) Text(s.offline),
                Text(s.chartUnavailable), TextButton(onPressed: () => ref.invalidate(chartProvider(key)), child: Text(s.retry))]);
              return Column(children: [DataStatus(fetchedAt: resource.fetchedAt, persian: p.persian,
                offline: resource.offline, stale: resource.stale, demo: resource.demo),
                if (!resource.demo && resource.source != 'cmc_history') Text(s.collectedChart),
                Directionality(textDirection: TextDirection.ltr, child: Semantics(label: s.chart,
                child: SizedBox(height: 220, child: LineChart(LineChartData(
                  lineBarsData: [LineChartBarData(spots: [for (final point in points)
                    FlSpot(point.time.difference(points.first.time).inSeconds.toDouble(), point.price)],
                    color: Theme.of(context).colorScheme.primary, barWidth: 3, dotData: const FlDotData(show: false))],
                  titlesData: const FlTitlesData(show: false), borderData: FlBorderData(show: false)),
                  duration: MediaQuery.of(context).disableAnimations ? Duration.zero : const Duration(milliseconds: 150))))),
                Wrap(spacing: Tokens.gutter, children: [Text(tehranDate(points.first.time, p.persian)), Text(tehranDate(points.last.time, p.persian))]),
                TextButton(onPressed: () => setState(() => showTable = !showTable), child: Text(s.chartTable)),
                if (showTable) for (final point in points) ListTile(title: Text(tehranDate(point.time, p.persian)),
                  subtitle: NumericText(usd(point.price, p.persian)))]);
            }),
          const SizedBox(height: Tokens.section), Text(s.volume), NumericText(usd(coin.volume, p.persian)),
          Text(s.marketCap), NumericText(usd(coin.marketCap, p.persian)),
          TextButton(onPressed: () => context.push('/coin/${coin.id}/news'), child: Text(s.news))]);
      })));
  }
}
