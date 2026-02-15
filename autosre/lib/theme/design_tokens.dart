import 'package:flutter/material.dart';

/// Centralized design tokens for the AutoSRE Deep Space theme.
///
/// All spacing, border-radius, elevation, and animation values should
/// reference these tokens rather than using hardcoded magic numbers.
/// This ensures visual consistency across the entire application.
class Spacing {
  Spacing._();

  /// 4dp — icon gaps, tight inline spacing
  static const double xs = 4;

  /// 8dp — standard compact spacing, chip margins
  static const double sm = 8;

  /// 12dp — card internal padding, toolbar padding
  static const double md = 12;

  /// 16dp — section spacing, card padding
  static const double lg = 16;

  /// 20dp — message bubble padding
  static const double xl = 20;

  /// 24dp — large section margins, heading gaps
  static const double xxl = 24;

  /// 32dp — page-level margins, large gaps
  static const double xxxl = 32;

  // Common EdgeInsets presets
  static const EdgeInsets paddingXs = EdgeInsets.all(xs);
  static const EdgeInsets paddingSm = EdgeInsets.all(sm);
  static const EdgeInsets paddingMd = EdgeInsets.all(md);
  static const EdgeInsets paddingLg = EdgeInsets.all(lg);
  static const EdgeInsets paddingXl = EdgeInsets.all(xl);
}

/// Standard border radius values.
class Radii {
  Radii._();

  /// 4dp — tiny elements (inline badges, code pills)
  static const double xs = 4;

  /// 6dp — small chips, compact badges
  static const double sm = 6;

  /// 8dp — status badges, tooltips, small containers
  static const double md = 8;

  /// 10dp — tool log cards, autocomplete overlays
  static const double lg = 10;

  /// 12dp — elevated cards, snackbars, dashboard cards
  static const double xl = 12;

  /// 16dp — primary cards, glass panels, icon buttons
  static const double xxl = 16;

  /// 20dp — message bubbles
  static const double bubble = 20;

  /// 24dp — input fields, search bars
  static const double input = 24;

  /// 30dp — prompt input pill
  static const double pill = 30;

  // Common BorderRadius presets
  static BorderRadius borderXs = BorderRadius.circular(xs);
  static BorderRadius borderSm = BorderRadius.circular(sm);
  static BorderRadius borderMd = BorderRadius.circular(md);
  static BorderRadius borderLg = BorderRadius.circular(lg);
  static BorderRadius borderXl = BorderRadius.circular(xl);
  static BorderRadius borderXxl = BorderRadius.circular(xxl);
  static BorderRadius borderPill = BorderRadius.circular(pill);
}

/// Standard elevation / shadow presets.
class Elevations {
  Elevations._();

  /// No elevation
  static const double none = 0;

  /// Subtle lift for cards
  static const double low = 4;

  /// Standard card elevation
  static const double medium = 8;

  /// Floating elements (dropdowns, dialogs)
  static const double high = 16;

  /// Top-level overlays (modals, drawers)
  static const double overlay = 24;
}

/// Standard animation durations for consistent motion.
class Durations {
  Durations._();

  /// 100ms — micro-interactions (opacity, color)
  static const Duration instant = Duration(milliseconds: 100);

  /// 200ms — hover effects, small transitions
  static const Duration fast = Duration(milliseconds: 200);

  /// 250ms — card expand/collapse
  static const Duration normal = Duration(milliseconds: 250);

  /// 350ms — panel slide, page transitions
  static const Duration slow = Duration(milliseconds: 350);

  /// 500ms — large layout changes
  static const Duration slower = Duration(milliseconds: 500);
}

/// Severity color tokens — consistent severity colors across all widgets.
///
/// Use these instead of hardcoding severity colors in individual widgets.
class SeverityColors {
  SeverityColors._();

  /// Critical/Emergency/Alert severity (bright red)
  static const Color critical = Color(0xFFFF1744);

  /// High severity (coral red)
  static const Color high = Color(0xFFFF6B6B);

  /// Queue service type (pink)
  static const Color queue = Color(0xFFE91E63);
}
