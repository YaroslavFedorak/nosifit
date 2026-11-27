import SwiftUI

@MainActor
final class TodayModel: ObservableObject {
    @Published private(set) var today: DashboardToday?
    @Published private(set) var loading = false
    @Published private(set) var error: LocalizedStringKey?

    private let api: APIClient

    init(api: APIClient) { self.api = api }

    func refresh() async {
        guard !loading else { return }
        loading = true
        defer { loading = false }
        do {
            today = try await api.get("dashboard/today", as: DashboardToday.self)
            error = nil
        } catch {
            self.error = message(for: error)
        }
    }
}

struct TodayView: View {
    @StateObject private var model: TodayModel

    init(api: APIClient) {
        _model = StateObject(wrappedValue: TodayModel(api: api))
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: NosiSpace.md) {
                    if let today = model.today {
                        content(today)
                    } else if let error = model.error {
                        VStack(alignment: .leading, spacing: NosiSpace.sm) {
                            Text(error).foregroundStyle(NosiColor.error)
                            Button("retry") { Task { await model.refresh() } }.buttonStyle(.bordered)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    } else {
                        ProgressView().padding(.top, NosiSpace.xl)
                    }
                }
                .padding(NosiSpace.md)
            }
            .refreshable { await model.refresh() }
            .background(NosiColor.paper)
            .navigationTitle("today.title")
        }
        .task { if model.today == nil { await model.refresh() } }
    }

    @ViewBuilder
    private func content(_ today: DashboardToday) -> some View {
        VStack(alignment: .leading, spacing: NosiSpace.xs) {
            Text("today.score").font(.subheadline.weight(.medium)).foregroundStyle(NosiColor.muted)
            if let score = today.dailyScore {
                Text("\(Int(score.rounded()))")
                    .font(.system(size: 40, weight: .semibold))
                    .foregroundStyle(NosiColor.accent)
                ScoreBar(score: score, tone: NosiColor.accent)
            } else {
                Text("today.no_score").font(.title3)
            }
        }
        .card()

        ModuleCard(
            title: "today.training",
            tone: NosiColor.training,
            score: today.training.score,
            detail: today.training.completed
                ? String(format: String(localized: "today.training_done"), Int(today.training.duration.rounded()), today.training.exerciseCount)
                : String(localized: "today.training_none")
        )
        ModuleCard(
            title: "today.nutrition",
            tone: NosiColor.nutrition,
            score: today.nutrition.score,
            detail: String(
                format: String(localized: "today.nutrition_value"),
                Int(today.nutrition.calories.rounded()), Int(today.nutrition.protein.rounded()), today.nutrition.water
            )
        )
        ModuleCard(
            title: "today.recovery",
            tone: NosiColor.recovery,
            score: today.recovery.score,
            detail: String(
                format: String(localized: "today.recovery_value"),
                today.recovery.habitsCompleted, today.recovery.habitsTotal, today.recovery.sleepHours
            )
        )
    }
}

private struct ModuleCard: View {
    let title: LocalizedStringKey
    let tone: Color
    let score: Double?
    let detail: String

    var body: some View {
        HStack(alignment: .top, spacing: NosiSpace.sm) {
            RoundedRectangle(cornerRadius: 2).fill(tone).frame(width: 4, height: 44)
            VStack(alignment: .leading, spacing: 4) {
                Text(title).font(.headline)
                Text(detail).font(.subheadline).foregroundStyle(NosiColor.ink2)
                if let score { ScoreBar(score: score, tone: tone).padding(.top, 4) }
            }
            Spacer(minLength: 0)
            if let score {
                Text("\(Int(score.rounded()))").font(.title2.weight(.semibold)).foregroundStyle(tone)
            }
        }
        .card()
    }
}

private struct ScoreBar: View {
    let score: Double
    let tone: Color

    var body: some View {
        GeometryReader { proxy in
            ZStack(alignment: .leading) {
                Capsule().fill(NosiColor.paper4)
                Capsule().fill(tone).frame(width: proxy.size.width * min(max(score / 100, 0), 1))
            }
        }
        .frame(height: 6)
    }
}
