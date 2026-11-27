import SwiftUI

/// The bottom tabs, in the order of the website's phone tab bar.
struct HomeView: View {
    @EnvironmentObject private var session: Session
    let user: MobileUser

    var body: some View {
        TabView {
            TodayView(api: session.api)
                .tabItem { Label("tab.today", systemImage: "sun.max") }
            ComingSoonView(path: "app/nutrition")
                .tabItem { Label("tab.nutrition", systemImage: "fork.knife") }
            ComingSoonView(path: "app/training")
                .tabItem { Label("tab.training", systemImage: "dumbbell") }
            ComingSoonView(path: "app/recovery")
                .tabItem { Label("tab.recovery", systemImage: "moon.zzz") }
            ProfileView(user: user)
                .tabItem { Label("tab.profile", systemImage: "person") }
        }
    }
}

private struct ComingSoonView: View {
    @EnvironmentObject private var session: Session
    let path: String

    var body: some View {
        VStack(alignment: .leading, spacing: NosiSpace.md) {
            Text("coming_soon").foregroundStyle(NosiColor.ink2)
            Link("open_website", destination: session.serverURL.appendingPathComponent(path))
            Spacer()
        }
        .padding(NosiSpace.lg)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(NosiColor.paper)
    }
}

private struct ProfileView: View {
    @EnvironmentObject private var session: Session
    let user: MobileUser

    /// The product's version (VERSION in the repository, MARKETING_VERSION in project.yml).
    private var appVersion: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "?"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: NosiSpace.sm) {
            Text("profile.signed_in_as").foregroundStyle(NosiColor.muted)
            Text(user.name).font(.title2.weight(.semibold))
            Text(user.email).foregroundStyle(NosiColor.ink2)
            Button("profile.logout") { Task { await session.signOut() } }
                .buttonStyle(.bordered)
                .padding(.top, NosiSpace.sm)
            Text(verbatim: "NosiFit \(appVersion)")
                .font(.footnote)
                .foregroundStyle(NosiColor.muted)
            Spacer()
        }
        .padding(NosiSpace.lg)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(NosiColor.paper)
    }
}
