import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:nabz_coin/core/state.dart';

void main() {
  test('Watchlist survives provider destruction and restart', () async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final first = ProviderContainer(overrides: [preferencesProvider.overrideWithValue(prefs)]);
    await first.read(appStateProvider.notifier).toggleCoin(1);
    first.dispose();
    final restarted = ProviderContainer(overrides: [preferencesProvider.overrideWithValue(prefs)]);
    expect(restarted.read(appStateProvider).watch, contains(1));
    await restarted.read(appStateProvider.notifier).toggleCoin(1);
    expect(restarted.read(appStateProvider).watch, isEmpty);
    restarted.dispose();
  });
  test('Rapid toggles serialize writes without losing additions', () async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final container = ProviderContainer(overrides: [preferencesProvider.overrideWithValue(prefs)]);
    final controller = container.read(appStateProvider.notifier);
    await Future.wait([controller.toggleCoin(1), controller.toggleCoin(1027), controller.toggleCoin(1)]);
    container.dispose();
    final restarted = ProviderContainer(overrides: [preferencesProvider.overrideWithValue(prefs)]);
    expect(restarted.read(appStateProvider).watch, {1027});
    restarted.dispose();
  });
}
