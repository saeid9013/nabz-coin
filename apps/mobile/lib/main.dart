import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'l10n/app_localizations.dart';
import 'core/state.dart';
import 'core/theme.dart';
import 'features/market/market_page.dart';
import 'features/news/news_page.dart';
import 'features/settings/settings_page.dart';
import 'features/coin_detail/coin_detail_page.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  runApp(ProviderScope(overrides: [preferencesProvider.overrideWithValue(prefs)], child: const NabzApp()));
}

final router = GoRouter(errorBuilder: (context, state) => Scaffold(
  appBar: AppBar(title: Text(AppLocalizations.of(context).appName)),
  body: Center(child: Text(AppLocalizations.of(context).empty))), routes: [
  StatefulShellRoute.indexedStack(builder: (c, s, shell) => Shell(shell), branches: [
    StatefulShellBranch(routes: [GoRoute(path: '/', builder: (c, s) => const MarketPage())]),
    StatefulShellBranch(routes: [GoRoute(path: '/news', builder: (c, s) => const NewsPage())]),
    StatefulShellBranch(routes: [GoRoute(path: '/watchlist', builder: (c, s) => const MarketPage(watchOnly: true))]),
    StatefulShellBranch(routes: [GoRoute(path: '/settings', builder: (c, s) => const SettingsPage())])]),
  GoRoute(path: '/coin/:id', builder: (c, s) => CoinDetailPage(int.tryParse(s.pathParameters['id']!) ?? 0)),
  GoRoute(path: '/coin/:id/news', builder: (c, s) => Scaffold(appBar: AppBar(title: Text(AppLocalizations.of(c).news)),
    body: SafeArea(child: NewsPage(coinId: int.tryParse(s.pathParameters['id']!) ?? 0)))),
  GoRoute(path: '/news/:id', builder: (c, s) => NewsDetailPage(s.pathParameters['id']!))]);

class NabzApp extends ConsumerWidget {
  const NabzApp({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final p = ref.watch(appStateProvider);
    return MaterialApp.router(debugShowCheckedModeBanner: false, routerConfig: router,
      locale: const Locale('fa'), supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      theme: Tokens.theme(Brightness.light), darkTheme: Tokens.theme(Brightness.dark), themeMode: p.theme,
      builder: (context, child) => MediaQuery(data: MediaQuery.of(context).copyWith(
        textScaler: MediaQuery.textScalerOf(context).clamp(minScaleFactor: p.scale)), child: child!));
  }
}

class Shell extends StatelessWidget {
  const Shell(this.shell, {super.key});
  final StatefulNavigationShell shell;
  @override
  Widget build(BuildContext context) {
    final s = AppLocalizations.of(context);
    final labels = [s.market, s.news, s.watchlist, s.settings];
    final extraText = (MediaQuery.textScalerOf(context).scale(14) - 14).clamp(0, double.infinity).toDouble();
    return Scaffold(appBar: AppBar(toolbarHeight: 56 + extraText * 2,
      title: Text('${s.appName} · ${labels[shell.currentIndex]}', maxLines: 2)),
      body: SafeArea(child: shell), bottomNavigationBar: NavigationBar(selectedIndex: shell.currentIndex,
        height: 80 + extraText * 3,
        onDestinationSelected: (i) => shell.goBranch(i), destinations: [
          NavigationDestination(icon: const Icon(Icons.bar_chart_outlined), label: s.market),
          NavigationDestination(icon: const Icon(Icons.article_outlined), label: s.news),
          NavigationDestination(icon: const Icon(Icons.star_outline), label: s.watchlist),
          NavigationDestination(icon: const Icon(Icons.settings_outlined), label: s.settings)]));
  }
}
