import 'package:flutter_test/flutter_test.dart';
import 'package:nabz_coin/core/formatters.dart';

void main() {
  test('Nonzero small prices preserve magnitude', () {
    expect(usd(0.0000000000123, false), contains('e-11'));
    expect(usd(1e-100, false), contains('e-100'));
    expect(usd(62450.25, false), '\$62450.25');
  });
  test('Signed numbers and symbols keep their logical order', () {
    expect(digits('-2.40% BTC', true), '-۲.۴۰% BTC');
  });
  test('Tehran date crosses UTC day boundary into Jalali new year', () {
    expect(tehranDate(DateTime.utc(2024, 3, 19, 21), false), '1403/01/01 00:30');
  });
}
