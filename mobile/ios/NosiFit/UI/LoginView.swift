import SwiftUI

struct LoginView: View {
    @EnvironmentObject private var session: Session
    @State private var email = ""
    @State private var password = ""
    @State private var server = ""
    @State private var showServer = false
    @State private var busy = false
    @State private var error: LocalizedStringKey?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: NosiSpace.md) {
                Text(verbatim: "NosiFit")
                    .font(.system(size: 40, weight: .semibold))
                    .foregroundStyle(NosiColor.accent)
                Text("login.subtitle").foregroundStyle(NosiColor.muted)

                Text("login.title").font(.title2.weight(.semibold)).padding(.top, NosiSpace.md)

                TextField("login.email", text: $email)
                    .textContentType(.username)
                    .keyboardType(.emailAddress)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .fieldStyle()
                SecureField("login.password", text: $password)
                    .textContentType(.password)
                    .submitLabel(.go)
                    .onSubmit(submit)
                    .fieldStyle()

                if let error {
                    Text(error).foregroundStyle(NosiColor.error)
                }

                Button(action: submit) {
                    Group {
                        if busy { ProgressView().tint(NosiColor.accentInk) } else { Text("login.submit") }
                    }
                    .frame(maxWidth: .infinity, minHeight: 48)
                }
                .buttonStyle(.borderedProminent)
                .foregroundStyle(NosiColor.accentInk)
                .disabled(busy)

                Text("login.no_account").font(.callout).foregroundStyle(NosiColor.muted)

                Button("login.server") { showServer.toggle() }
                if showServer {
                    TextField("login.server", text: $server)
                        .keyboardType(.URL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .fieldStyle()
                    Text("login.server_hint").font(.footnote).foregroundStyle(NosiColor.muted)
                }
            }
            .padding(.horizontal, NosiSpace.lg)
            .padding(.vertical, NosiSpace.xl)
        }
        .onAppear { server = session.serverAddress }
    }

    private func submit() {
        guard !busy else { return }
        guard !email.trimmingCharacters(in: .whitespaces).isEmpty, !password.isEmpty else {
            error = "error.invalid_input"
            return
        }
        busy = true
        error = nil
        session.serverAddress = server
        Task {
            defer { busy = false }
            do {
                try await session.signIn(email: email, password: password)
            } catch {
                self.error = message(for: error)
            }
        }
    }
}

private extension View {
    func fieldStyle() -> some View {
        padding(NosiSpace.sm)
            .background(NosiColor.paper2, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 8, style: .continuous).stroke(NosiColor.rule))
    }
}
