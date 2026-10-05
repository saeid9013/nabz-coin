import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../l10n/app_localizations.dart';
import '../../core/state.dart';
import '../../core/theme.dart';

class SettingsPage extends ConsumerWidget {
  const SettingsPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = AppLocalizations.of(context), p = ref.watch(appStateProvider);
    final controller = ref.read(appStateProvider.notifier);
    return ListView(padding: const EdgeInsets.all(Tokens.gutter), children: [
      Text(s.theme, style: Theme.of(context).textTheme.titleLarge),
      DropdownButton<ThemeMode>(isExpanded: true, value: p.theme,
        items: [DropdownMenuItem(value: ThemeMode.system, child: Text(s.system)),
          DropdownMenuItem(value: ThemeMode.light, child: Text(s.light)),
          DropdownMenuItem(value: ThemeMode.dark, child: Text(s.dark))], onChanged: (v) => controller.update(theme: v)),
      const SizedBox(height: Tokens.section), Text(s.textSize),
      Slider(min: 1, max: 1.5, divisions: 5, value: p.scale, label: '${p.scale.toStringAsFixed(1)}×',
        onChanged: (v) => controller.update(scale: v)),
      SwitchListTile(title: Text(s.persianDigits), value: p.persian, onChanged: (v) => controller.update(persian: v)),
      const SizedBox(height: Tokens.section), Text(s.about)]);
  }
}
