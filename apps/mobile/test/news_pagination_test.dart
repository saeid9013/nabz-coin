import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:nabz_coin/core/models.dart';
import 'package:nabz_coin/core/repository.dart';
import 'package:nabz_coin/core/state.dart';
import 'package:nabz_coin/features/news/news_page.dart';
import 'package:nabz_coin/l10n/app_localizations.dart';

Article article(String id) => Article(id: id, title: 'خبر $id', summary: '',
  url: 'https://example.com/$id', publisher: 'آزمون', publishedAt: DateTime.now().toUtc(),
  coinIds: [1], demo: false, translated: true);
Resource<NewsBatch> batch(List<Article> articles, String? cursor) =>
  Resource(NewsBatch(articles, cursor), fetchedAt: DateTime.now().toUtc());

class PendingRepository extends Repository {
  PendingRepository(SharedPreferences prefs) : super(prefs, demo: false);
  final next = Completer<Resource<NewsBatch>>();
  int firstCalls = 0, pageCalls = 0;
  @override
  Future<Resource<NewsBatch>> news({int? coinId, String? cursor}) async {
    if (cursor != null) { pageCalls++; return next.future; }
    firstCalls++;
    return batch([article(firstCalls == 1 ? 'initial' : 'refreshed')], 'next');
  }
}

void main() {
  testWidgets('Refresh ignores a previously requested next page', (tester) async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final repository = PendingRepository(prefs);
    await tester.pumpWidget(ProviderScope(overrides: [
      preferencesProvider.overrideWithValue(prefs), repositoryProvider.overrideWithValue(repository)],
      child: MaterialApp(locale: const Locale('fa'),
        supportedLocales: AppLocalizations.supportedLocales,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        home: const Scaffold(body: NewsPage()))));
    await tester.pumpAndSettle();
    final more = find.byType(FilledButton);
    await tester.ensureVisible(more);
    await tester.tap(more);
    await tester.pump();
    expect(repository.pageCalls, 1);
    final refresh = tester.state<RefreshIndicatorState>(find.byType(RefreshIndicator)).show();
    await tester.pump(const Duration(seconds: 1));
    await tester.pump(const Duration(seconds: 1));
    await tester.pump(const Duration(seconds: 1));
    await refresh;
    repository.next.complete(batch([article('obsolete')], null));
    await tester.pumpAndSettle();
    expect(repository.firstCalls, 2);
    expect(find.text('خبر obsolete'), findsNothing);
    expect(find.text('خبر refreshed'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
