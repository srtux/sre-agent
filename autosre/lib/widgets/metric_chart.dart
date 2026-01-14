
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/adk_schema.dart';

class MetricCorrelationChart extends StatelessWidget {
  final MetricSeries series;

  const MetricCorrelationChart({super.key, required this.series});

  @override
  Widget build(BuildContext context) {
    if (series.points.isEmpty) {
        return const Center(child: Text("No metric data"));
    }

    final sortedPoints = List<MetricPoint>.from(series.points)
      ..sort((a, b) => a.timestamp.compareTo(b.timestamp));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.all(8.0),
          child: Text("Metric: ${series.metricName}", style: Theme.of(context).textTheme.titleMedium),
        ),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: LineChart(
              LineChartData(
                gridData: const FlGridData(show: true),
                titlesData: FlTitlesData(
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 30,
                      interval: (sortedPoints.length / 5).ceil().toDouble(), // Show approx 5 labels
                      getTitlesWidget: (value, meta) {
                        int index = value.toInt();
                        if (index >= 0 && index < sortedPoints.length) {
                             return Padding(
                               padding: const EdgeInsets.only(top: 8.0),
                               child: Text(
                                 DateFormat('HH:mm').format(sortedPoints[index].timestamp),
                                 style: const TextStyle(fontSize: 10),
                               ),
                             );
                        }
                        return const Text('');
                      },
                    ),
                  ),
                  leftTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: true, reservedSize: 40)
                  ),
                  topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                ),
                borderData: FlBorderData(show: true),
                lineBarsData: [
                  LineChartBarData(
                    spots: sortedPoints.asMap().entries.map((e) {
                      return FlSpot(e.key.toDouble(), e.value.value);
                    }).toList(),
                    isCurved: true,
                    color: Theme.of(context).colorScheme.primary,
                    barWidth: 2,
                    dotData: FlDotData(
                        show: true,
                        getDotPainter: (spot, percent, barData, index) {
                             final point = sortedPoints[index];
                             if (point.isAnomaly) {
                                 return FlDotCirclePainter(
                                     radius: 6,
                                     color: Theme.of(context).colorScheme.error,
                                     strokeWidth: 2,
                                     strokeColor: Colors.white,
                                 );
                             }
                             return FlDotCirclePainter(radius: 0, color: Colors.transparent); // Hide normal dots
                        }
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}
