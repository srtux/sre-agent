import 'package:flutter/material.dart';

import 'pages/conversation_page.dart';
import 'theme/app_theme.dart';

class SreNexusApp extends StatelessWidget {
  const SreNexusApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AutoSRE',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      home: const ConversationPage(),
    );
  }
}
