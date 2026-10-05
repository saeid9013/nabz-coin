import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:nabz_coin/core/models.dart';
import 'package:nabz_coin/core/state.dart';
import 'package:nabz_coin/core/theme.dart';
import 'package:nabz_coin/core/widgets.dart';
import 'package:nabz_coin/l10n/app_localizations.dart';

void main() {
  for (final width in [360.0, 412.0]) {
    for (final brightness in Brightness.values) {
      testWidgets('RTL market row at $width, $brightness, large text', (tester) async {
        SharedPreferences.setMockInitialValues({});
        final prefs = await SharedPreferences.getInstance();
        tester.view.physicalSize = Size(width, 900);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        await tester.pumpWidget(ProviderScope(overrides: [preferencesProvider.overrideWithValue(prefs)],
          child: MaterialApp(locale: const Locale('fa'), theme: Tokens.theme(brightness),
            supportedLocales: AppLocalizations.supportedLocales,
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            builder: (c, child) => MediaQuery(data: MediaQuery.of(c).copyWith(textScaler: const TextScaler.linear(2)), child: child!),
            home: Scaffold(body: ListView(children: [CoinTile(const Coin(id: 1, rank: 1,
              name: 'نام فارسی طولانی برای بررسی خوانایی بازار', symbol: 'BTC', price: 62450.25,
              change: -2.4, volume: 100, marketCap: 1000), onTap: () {})])))));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        expect(Directionality.of(tester.element(find.byType(CoinTile))), TextDirection.rtl);
        expect(find.byTooltip('افزودن به واچ‌لیست'), findsOneWidget);
      });
    }
  }
}
