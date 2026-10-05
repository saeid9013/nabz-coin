import 'package:flutter/material.dart';

abstract final class Tokens {
  static const gap = 8.0, gutter = 16.0, section = 24.0, radius = 16.0;
  static const accent = Color(0xFF2563EB);
  static const lightBackground = Color(0xFFF8FAFC), darkBackground = Color(0xFF0B1220);
  static const lightSurface = Color(0xFFFFFFFF), darkSurface = Color(0xFF172033);
  static const lightText = Color(0xFF0F172A), darkText = Color(0xFFF8FAFC);
  static const lightSecondary = Color(0xFF475569), darkSecondary = Color(0xFFCBD5E1);
  static Color rise(BuildContext c) => Theme.of(c).brightness == Brightness.dark
    ? const Color(0xFF86EFAC) : const Color(0xFF166534);
  static Color fall(BuildContext c) => Theme.of(c).brightness == Brightness.dark
    ? const Color(0xFFFCA5A5) : const Color(0xFFB91C1C);
  static ThemeData theme(Brightness brightness) {
    final dark = brightness == Brightness.dark;
    return ThemeData(useMaterial3: true, brightness: brightness, fontFamily: 'Vazirmatn',
      colorScheme: ColorScheme.fromSeed(seedColor: accent, brightness: brightness,
        surface: dark ? darkSurface : lightSurface,
        onSurface: dark ? darkText : lightText, onSurfaceVariant: dark ? darkSecondary : lightSecondary),
      scaffoldBackgroundColor: dark ? darkBackground : lightBackground,
      visualDensity: VisualDensity.standard,
      materialTapTargetSize: MaterialTapTargetSize.padded,
      textButtonTheme: TextButtonThemeData(style: TextButton.styleFrom(minimumSize: const Size(48, 48))),
      filledButtonTheme: FilledButtonThemeData(style: FilledButton.styleFrom(minimumSize: const Size(48, 48))),
      iconButtonTheme: const IconButtonThemeData(style: ButtonStyle(minimumSize: WidgetStatePropertyAll(Size(48, 48)))),
      inputDecorationTheme: const InputDecorationTheme(border: OutlineInputBorder()),
      cardTheme: CardThemeData(shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(radius))),
      textTheme: const TextTheme(bodyMedium: TextStyle(fontSize: 16, height: 1.5)));
  }
}
