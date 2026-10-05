import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:nabz_coin/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets('Market to coin to persistent watchlist and saved news', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await app.main();
    await tester.pumpAndSettle();
    await tester.tap(find.text('بیت‌کوین').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('افزودن به واچ‌لیست'));
    await tester.pumpAndSettle();
    expect(find.text('حذف از واچ‌لیست'), findsOneWidget);
    await tester.pageBack();
    await tester.pumpAndSettle();
    await tester.tap(find.text('واچ‌لیست').last);
    await tester.pumpAndSettle();
    expect(find.text('بیت‌کوین'), findsOneWidget);
    await tester.tap(find.text('اخبار').last);
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('ذخیره خبر').first);
    await tester.pumpAndSettle();
    expect(find.byTooltip('حذف از ذخیره‌ها'), findsOneWidget);
    await tester.tap(find.text('خواندن خبر').first);
    await tester.pumpAndSettle();
    expect(find.byIcon(Icons.open_in_new), findsOneWidget);
  });
}
