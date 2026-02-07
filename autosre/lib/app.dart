import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';
import 'pages/conversation_page.dart';
import 'pages/login_page.dart';
import 'services/auth_service.dart';
import 'services/connectivity_service.dart';
import 'services/project_service.dart';
import 'services/session_service.dart';
import 'services/tool_config_service.dart';
import 'services/prompt_history_service.dart';
import 'services/dashboard_state.dart';
import 'services/explorer_query_service.dart';
import 'theme/app_theme.dart';

class SreNexusApp extends StatelessWidget {
  const SreNexusApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthService()..init()),
        ChangeNotifierProvider(create: (_) => ConnectivityService()),
        Provider(create: (_) => ProjectService()),
        Provider(create: (_) => SessionService()),
        Provider(create: (_) => ToolConfigService()),
        Provider(create: (_) => PromptHistoryService()),
        ChangeNotifierProvider(create: (_) => DashboardState()),
        ProxyProvider<DashboardState, ExplorerQueryService>(
          update: (_, dashState, _) => ExplorerQueryService(
            dashboardState: dashState,
            clientFactory: () => http.Client(),
          ),
        ),
      ],
      child: MaterialApp(
        title: 'AutoSRE',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.darkTheme,
        home: const AuthWrapper(),
      ),
    );
  }
}

class AuthWrapper extends StatelessWidget {
  const AuthWrapper({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<AuthService>(
      builder: (context, auth, _) {
        if (auth.isLoading) {
          return const Scaffold(
            backgroundColor: AppColors.backgroundDark,
            body: Center(
              child: CircularProgressIndicator(color: AppColors.primaryTeal),
            ),
          );
        }

        if (!auth.isAuthenticated) {
          return const LoginPage();
        }

        return const ConversationPage();
      },
    );
  }
}
