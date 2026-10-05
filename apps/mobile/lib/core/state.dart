import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

final preferencesProvider = Provider<SharedPreferences>((ref) => throw StateError('Preferences not initialized'));
final appStateProvider = NotifierProvider<AppState, Preferences>(AppState.new);

class Preferences {
  Preferences({this.watch = const {}, this.saved = const {}, this.theme = ThemeMode.system,
    this.scale = 1, this.persian = true});
  final Set<int> watch;
  final Set<String> saved;
  final ThemeMode theme;
  final double scale;
  final bool persian;
}

class AppState extends Notifier<Preferences> {
  Future<void> _writes = Future.value();
  SharedPreferences get storage => ref.read(preferencesProvider);
  @override
  Preferences build() => Preferences(
    watch: (storage.getStringList('watch') ?? []).map(int.tryParse).whereType<int>().where((i) => i > 0).toSet(),
    saved: (storage.getStringList('saved') ?? []).toSet(),
    theme: ThemeMode.values[(storage.getInt('theme') ?? 0).clamp(0, ThemeMode.values.length - 1).toInt()],
    scale: (storage.getDouble('scale') ?? 1).clamp(1, 1.5).toDouble(), persian: storage.getBool('persian') ?? true);
  Future<void> update({Set<int>? watch, Set<String>? saved, ThemeMode? theme, double? scale, bool? persian}) async {
    final next = Preferences(watch: watch ?? state.watch, saved: saved ?? state.saved,
      theme: theme ?? state.theme, scale: scale ?? state.scale, persian: persian ?? state.persian);
    state = next;
    _writes = _writes.then((_) async {
      await storage.setStringList('watch', next.watch.map((v) => '$v').toList());
      await storage.setStringList('saved', next.saved.toList());
      await storage.setInt('theme', next.theme.index);
      await storage.setDouble('scale', next.scale);
      await storage.setBool('persian', next.persian);
    });
    await _writes;
  }
  Future<void> toggleCoin(int id) => update(watch: state.watch.contains(id)
    ? ({...state.watch}..remove(id)) : ({...state.watch}..add(id)));
  Future<void> toggleArticle(String id) => update(saved: state.saved.contains(id)
    ? ({...state.saved}..remove(id)) : ({...state.saved}..add(id)));
}
