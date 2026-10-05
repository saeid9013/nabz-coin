import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:nabz_coin/core/models.dart';
import 'package:nabz_coin/core/repository.dart';

class ControlledRepository extends Repository {
  ControlledRepository(SharedPreferences preferences) : super(preferences);
  final pending = <String, Completer<Resource<List<ChartPoint>>>>{};
  @override
  Future<Resource<List<ChartPoint>>> chart(int id, String range) =>
    (pending[range] ??= Completer<Resource<List<ChartPoint>>>()).future;
}

void main() {
  test('Late previous range cannot replace data for currently selected range', () async {
    SharedPreferences.setMockInitialValues({});
    final repository = ControlledRepository(await SharedPreferences.getInstance());
    final container = ProviderContainer(overrides: [repositoryProvider.overrideWithValue(repository)]);
    const oldKey = (id: 1, range: '7d'), currentKey = (id: 1, range: '30d');
    final oldListener = container.listen(chartProvider(oldKey), (_, next) {});
    final currentListener = container.listen(chartProvider(currentKey), (_, next) {});
    final t = DateTime.utc(2026, 10, 5);
    repository.pending['30d']!.complete(Resource([ChartPoint(t, 30)], fetchedAt: t));
    final selected = await container.read(chartProvider(currentKey).future);
    expect(selected.data.single.price, 30);
    repository.pending['7d']!.complete(Resource([ChartPoint(t, 7)], fetchedAt: t));
    await container.read(chartProvider(oldKey).future);
    expect(container.read(chartProvider(currentKey)).requireValue.data.single.price, 30);
    oldListener.close(); currentListener.close(); container.dispose();
  });
}
