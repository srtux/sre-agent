
import 'package:flutter/material.dart';
import '../models/adk_schema.dart';

class LogPatternViewer extends StatelessWidget {
  final List<LogPattern> patterns;

  const LogPatternViewer({super.key, required this.patterns});

  @override
  Widget build(BuildContext context) {
      if (patterns.isEmpty) {
          return const Center(child: Text("No significant log patterns found."));
      }

      return SingleChildScrollView(
          scrollDirection: Axis.vertical,
          child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                  columns: const [
                      DataColumn(label: Text("Count", style: TextStyle(fontWeight: FontWeight.bold))),
                      DataColumn(label: Text("Severity", style: TextStyle(fontWeight: FontWeight.bold))),
                      DataColumn(label: Text("Pattern Template", style: TextStyle(fontWeight: FontWeight.bold))),
                  ],
                  rows: patterns.map((p) {
                      // Determine dominan severity for coloring
                      String dominantSeverity = "INFO";
                      int max = 0;
                      p.severityCounts.forEach((k,v) {
                          if (v > max) {
                              max = v;
                              dominantSeverity = k;
                          }
                      });

                      Color? severityColor;
                      if (dominantSeverity == 'ERROR') severityColor = Theme.of(context).colorScheme.error;
                      if (dominantSeverity == 'WARNING') severityColor = Colors.orange;

                      return DataRow(cells: [
                          DataCell(Text(p.count.toString())),
                           DataCell(Container(
                               padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                               decoration: BoxDecoration(
                                   color: severityColor?.withValues(alpha: 0.2) ?? Colors.grey.withValues(alpha: 0.2),
                                   borderRadius: BorderRadius.circular(12),
                                   border: Border.all(color: severityColor ?? Colors.grey)
                               ),
                               child: Text(dominantSeverity, style: TextStyle(fontSize: 10, color: severityColor)),
                           )),
                          DataCell(Text(p.template, style: const TextStyle(fontFamily: 'monospace', fontSize: 12))),
                      ]);
                  }).toList(),
              ),
          ),
      );
  }
}
