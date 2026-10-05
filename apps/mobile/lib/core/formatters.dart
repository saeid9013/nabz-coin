import 'package:shamsi_date/shamsi_date.dart';
import '../l10n/app_localizations.dart';

String digits(String text, bool persian) {
  if (!persian) return text;
  const latin = '0123456789', fa = '۰۱۲۳۴۵۶۷۸۹';
  return text.split('').map((c) => latin.contains(c) ? fa[latin.indexOf(c)] : c).join();
}

String usd(double value, bool persian) {
  final abs = value.abs();
  // Scientific notation preserves every nonzero sub-cent value, including subnormal values.
  final raw = abs != 0 && abs < 0.000001 ? value.toStringAsExponential(5)
    : value.toStringAsFixed(abs < 1 ? 8 : 2);
  return digits('\$${raw}', persian);
}

String tehranDate(DateTime utc, bool persian) {
  // Tehran has used fixed UTC+03:30 since 2023; timestamps are modern market data.
  final t = utc.toUtc().add(const Duration(hours: 3, minutes: 30));
  final j = Jalali.fromDateTime(t);
  return digits('${j.year}/${j.month.toString().padLeft(2, '0')}/${j.day.toString().padLeft(2, '0')} '
    '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}', persian);
}

String relativeTime(DateTime utc, AppLocalizations s, bool persian, {DateTime? now}) {
  final age = (now ?? DateTime.now().toUtc()).difference(utc.toUtc());
  if (age.inMinutes < 1) return s.justNow;
  if (age.inHours < 1) return s.minutesAgo(digits('${age.inMinutes}', persian));
  if (age.inDays < 1) return s.hoursAgo(digits('${age.inHours}', persian));
  return s.daysAgo(digits('${age.inDays}', persian));
}
