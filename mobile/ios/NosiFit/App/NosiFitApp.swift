import SwiftUI

@main
struct NosiFitApp: App {
    @StateObject private var session = Session()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(session)
                .preferredColorScheme(.dark)
                .tint(NosiColor.accent)
        }
    }
}

struct RootView: View {
    @EnvironmentObject private var session: Session

    var body: some View {
        ZStack {
            NosiColor.paper.ignoresSafeArea()
            switch session.state {
            case .loading:
                ProgressView()
            case .signedOut:
                LoginView()
            case let .signedIn(user, consentRequired):
                if consentRequired {
                    ConsentView()
                } else {
                    // Keyed by account: after signing in as someone else the old data must not show.
                    HomeView(user: user).id(user.id)
                }
            }
        }
        .task {
            if session.state == .loading { await session.restore() }
        }
    }
}
