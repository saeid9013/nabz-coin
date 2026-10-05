import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../l10n/app_localizations.dart';
import 'models.dart';
import 'state.dart';
import 'formatters.dart';
import 'theme.dart';

class NumericText extends StatelessWidget {
  const NumericText(this.value, {super.key, this.style});
  final String value;
  final TextStyle? style;
  @override
  Widget build(BuildContext context) => Directionality(textDirection: TextDirection.ltr,
    child: Text(value, style: style, softWrap: true));
}

class DataStatus extends StatelessWidget {
  const DataStatus({super.key, required this.fetchedAt, required this.persian,
    this.offline = false, this.stale = false, this.demo = false});
  final DateTime fetchedAt;
  final bool persian, offline, stale, demo;
  @override
  Widget build(BuildContext context) {
    final s = AppLocalizations.of(context);
    return Semantics(liveRegion: true, child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      if (demo) Text(s.demo), if (offline) Text(s.offline), if (stale && !demo) Text(s.stale),
      Text('${s.updated}: ${tehranDate(fetchedAt, persian)} · ${relativeTime(fetchedAt, s, persian)}')]));
  }
}

class CoinAvatar extends StatelessWidget {
  const CoinAvatar(this.coin, {super.key});
  final Coin coin;
  @override
  Widget build(BuildContext context) {
    final uri = Uri.tryParse(coin.logoUrl ?? '');
    final allowed = uri != null && uri.scheme == 'https' && uri.host == 's2.coinmarketcap.com' && uri.port == 443;
    Widget fallback() => CircleAvatar(child: ExcludeSemantics(child: Text(coin.symbol.isEmpty ? '?' : coin.symbol.substring(0, 1))));
    if (!allowed) return fallback();
    return Image.network(uri.toString(), width: 40, height: 40,
      semanticLabel: coin.name, errorBuilder: (_, e, st) => fallback());
  }
}

class CoinTile extends ConsumerWidget {
  const CoinTile(this.coin, {super.key, required this.onTap});
  final Coin coin;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = AppLocalizations.of(context), p = ref.watch(appStateProvider);
    final up = coin.change >= 0;
    return Card(child: InkWell(onTap: onTap, borderRadius: BorderRadius.circular(Tokens.radius),
      child: Padding(padding: const EdgeInsets.all(Tokens.gutter), child: Column(
        crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [CoinAvatar(coin), const SizedBox(width: Tokens.gap),
            Expanded(child: Text(coin.name, style: Theme.of(context).textTheme.titleMedium)),
            IconButton(tooltip: p.watch.contains(coin.id) ? s.removeWatch : s.addWatch,
              onPressed: () => ref.read(appStateProvider.notifier).toggleCoin(coin.id),
              icon: Icon(p.watch.contains(coin.id) ? Icons.star : Icons.star_outline))]),
          NumericText('${coin.rank} · ${coin.symbol}'),
          const SizedBox(height: Tokens.gap),
          Wrap(spacing: Tokens.gutter, runSpacing: Tokens.gap, children: [
            NumericText(usd(coin.price, p.persian), style: Theme.of(context).textTheme.titleLarge),
            NumericText('${up ? '+' : ''}${digits(coin.change.toStringAsFixed(2), p.persian)}% ${up ? s.rise : s.fall}',
              style: TextStyle(color: up ? Tokens.rise(context) : Tokens.fall(context)))])]))));
  }
}

class RetryView extends StatelessWidget {
  const RetryView({super.key, required this.retry});
  final VoidCallback retry;
  @override
  Widget build(BuildContext context) {
    final s = AppLocalizations.of(context);
    return Center(child: Padding(padding: const EdgeInsets.all(Tokens.section), child: Column(
      mainAxisSize: MainAxisSize.min, children: [Text(s.networkError),
        const SizedBox(height: Tokens.gutter), FilledButton(onPressed: retry, child: Text(s.retry))])));
  }
}
