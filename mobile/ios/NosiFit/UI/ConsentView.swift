import SwiftUI

/// The same three explicit answers as the website's /consent page and the bot.
struct ConsentView: View {
    @EnvironmentObject private var session: Session
    @State private var privacy = false
    @State private var health = false
    @State private var age = false
    @State private var busy = false
    @State private var error: LocalizedStringKey?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: NosiSpace.md) {
                Text("consent.title").font(.title.weight(.semibold))
                Text("consent.body").foregroundStyle(NosiColor.ink2)
                Link("consent.policy_link", destination: session.serverURL.appendingPathComponent("privacy"))

                Toggle("consent.privacy", isOn: $privacy)
                Toggle("consent.health", isOn: $health)
                Toggle("consent.age", isOn: $age)

                if let error {
                    Text(error).foregroundStyle(NosiColor.error)
                }

                Button {
                    busy = true
                    error = nil
                    Task {
                        defer { busy = false }
                        do {
                            try await session.giveConsent()
                        } catch {
                            self.error = message(for: error)
                        }
                    }
                } label: {
                    Text("consent.submit").frame(maxWidth: .infinity, minHeight: 48)
                }
                .buttonStyle(.borderedProminent)
                .foregroundStyle(NosiColor.accentInk)
                .disabled(!(privacy && health && age) || busy)

                Button("profile.logout") { Task { await session.signOut() } }
            }
            .padding(NosiSpace.lg)
        }
    }
}
