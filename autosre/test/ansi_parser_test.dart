import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/utils/ansi_parser.dart';

void main() {
  test('AnsiParser parses simple text without ANSI codes', () {
    const text = 'Hello World';
    final span = AnsiParser.parse(text);

    expect(span.text, text);
    expect(span.children, isNull);
  });

  test('AnsiParser parses text with single ANSI color code', () {
    const text = '\x1B[31mRed Text\x1B[0m';
    final span = AnsiParser.parse(text);

    expect(span.children?.length, 1);
    expect(span.children?[0], isA<TextSpan>());
    final firstSpan = span.children?[0] as TextSpan;
    expect(firstSpan.text, 'Red Text');
    expect(firstSpan.style?.color, isNotNull);
    // Red bright is Color(0xFFFF5252) or Color(0xFFE57373) in my implementation
    // 31 is non-bright red -> 0xFFE57373
    expect(firstSpan.style?.color, const Color(0xFFE57373));
  });

  test('AnsiParser parses text with multiple colors and resets', () {
    const text = 'Normal \x1B[32mGreen\x1B[0m \x1B[34mBlue\x1B[0m';
    final span = AnsiParser.parse(text);

    // "Normal " (style: base)
    // "Green" (style: green)
    // " " (style: base)
    // "Blue" (style: blue)
    expect(span.children?.length, 4);

    expect((span.children?[0] as TextSpan).text, 'Normal ');
    expect((span.children?[1] as TextSpan).text, 'Green');
    expect((span.children?[1] as TextSpan).style?.color, const Color(0xFF81C784));

    expect((span.children?[2] as TextSpan).text, ' ');
    expect((span.children?[2] as TextSpan).style?.color, isNull); // Reset to base

    expect((span.children?[3] as TextSpan).text, 'Blue');
    expect((span.children?[3] as TextSpan).style?.color, const Color(0xFF64B5F6));
  });

  test('AnsiParser handles bold and combined codes', () {
    const text = '\x1B[1;36mBold Cyan\x1B[0m';
    final span = AnsiParser.parse(text);

    expect(span.children?.length, 1);
    final firstSpan = span.children?[0] as TextSpan;
    expect(firstSpan.text, 'Bold Cyan');
    expect(firstSpan.style?.fontWeight, FontWeight.bold);
    expect(firstSpan.style?.color, const Color(0xFF4DD0E1));
  });

  test('AnsiParser handles complex sequences like in the screenshot', () {
    // \x1b[36;21m
    const text = '\x1B[36;21mCyan-ish\x1B[0m';
    final span = AnsiParser.parse(text);

    expect(span.children?.length, 1);
    final firstSpan = span.children?[0] as TextSpan;
    expect(firstSpan.text, 'Cyan-ish');
    expect(firstSpan.style?.color, const Color(0xFF4DD0E1));
  });

  test('AnsiParser handles italic code (3)', () {
    const text = '\x1B[3mItalic Text\x1B[0m';
    final span = AnsiParser.parse(text);

    expect(span.children?.length, 1);
    final firstSpan = span.children?[0] as TextSpan;
    expect(firstSpan.text, 'Italic Text');
    expect(firstSpan.style?.fontStyle, FontStyle.italic);
  });

  test('AnsiParser handles underline code (4)', () {
    const text = '\x1B[4mUnderlined\x1B[0m';
    final span = AnsiParser.parse(text);

    expect(span.children?.length, 1);
    final firstSpan = span.children?[0] as TextSpan;
    expect(firstSpan.text, 'Underlined');
    expect(firstSpan.style?.decoration, TextDecoration.underline);
  });

  test('AnsiParser handles combined bold+italic+color', () {
    const text = '\x1B[1;3;31mBold Italic Red\x1B[0m';
    final span = AnsiParser.parse(text);

    expect(span.children?.length, 1);
    final firstSpan = span.children?[0] as TextSpan;
    expect(firstSpan.text, 'Bold Italic Red');
    expect(firstSpan.style?.fontWeight, FontWeight.bold);
    expect(firstSpan.style?.fontStyle, FontStyle.italic);
    expect(firstSpan.style?.color, const Color(0xFFE57373));
  });
}
