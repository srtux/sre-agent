
/// Visualization modes for the Agent Graph.
enum GraphViewMode {
  /// Default view: Standard coloring by node type.
  standard,

  /// Heatmap view: Colored by token consumption.
  tokenHeatmap,

  /// Heatmap view: Colored by error rate.
  errorHeatmap,

  /// Heatmap view: Colored by cost per node.
  costHeatmap,
}
