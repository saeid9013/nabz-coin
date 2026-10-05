import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nabz_coin/core/theme.dart';

double contrast(Color a, Color b) {
  final x = a.computeLuminance(), y = b.computeLuminance();
  return (max(x, y) + 0.05) / (min(x, y) + 0.05);
}
void main() {
  test('Normal primary and secondary text exceed WCAG 4.5 in both themes', () {
    for (final brightness in Brightness.values) {
      final theme = Tokens.theme(brightness), scheme = Tokens.theme(brightness).colorScheme;
      expect(contrast(scheme.onSurface, scheme.surface), greaterThanOrEqualTo(4.5));
      expect(contrast(scheme.onSurfaceVariant, scheme.surface), greaterThanOrEqualTo(4.5));
      expect(contrast(scheme.onSurface, theme.scaffoldBackgroundColor), greaterThanOrEqualTo(4.5));
    }
  });
}
