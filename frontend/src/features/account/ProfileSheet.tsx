import { useState, type FormEvent } from "react";
import { useUpdateProfile } from "../../api/mutations";
import type { AccountSummary } from "../../api/types";
import { useT } from "../../i18n";
import { useServerText } from "../../i18n/server";
import { parseDecimal } from "../../lib/format";
import { Button } from "../../ui/Button";
import { Chips, type Option } from "../../ui/Choice";
import { SelectField, TextField } from "../../ui/Field";
import { Sheet } from "../../ui/Sheet";

const RANGES = { age: [16, 120], height: [50, 272], weight: [20, 400], workouts: [0, 14] } as const;

const within = (text: string, [min, max]: readonly [number, number], whole: boolean): number | null | "bad" => {
  if (text.trim() === "") return null;
  const value = parseDecimal(text);
  if (value === null || value < min || value > max || (whole && !Number.isInteger(value))) return "bad";
  return value;
};

/**
 * The parameters the calorie and water targets are calculated from. Every
 * field is optional; the targets appear once age, height, weight and sex are known.
 */
export function ProfileSheet({ account, onClose }: { account: AccountSummary; onClose: () => void }) {
  const { t } = useT();
  const text = useServerText();
  const update = useUpdateProfile();
  const { profile, options } = account;
  const [name, setName] = useState(account.user.name);
  const [goal, setGoal] = useState(profile.goal ?? "");
  const [gender, setGender] = useState(profile.gender ?? "");
  const [age, setAge] = useState(profile.age != null ? String(profile.age) : "");
  const [height, setHeight] = useState(profile.height != null ? String(profile.height) : "");
  const [weight, setWeight] = useState(profile.weight != null ? String(profile.weight) : "");
  const [activity, setActivity] = useState(profile.activity ?? "");
  const [experience, setExperience] = useState(profile.experience ?? "");
  const [workouts, setWorkouts] = useState(profile.workouts_per_week != null ? String(profile.workouts_per_week) : "");
  const [location, setLocation] = useState(profile.training_location ?? "home");
  const [touched, setTouched] = useState(false);

  const parsed = {
    age: within(age, RANGES.age, true),
    height: within(height, RANGES.height, false),
    weight: within(weight, RANGES.weight, false),
    workouts: within(workouts, RANGES.workouts, true),
  };
  const errors = {
    name: name.trim() ? null : t("profile.error.name"),
    age: parsed.age === "bad" ? t("profile.error.age") : null,
    height: parsed.height === "bad" ? t("profile.error.height") : null,
    weight: parsed.weight === "bad" ? t("profile.error.weight") : null,
    workouts: parsed.workouts === "bad" ? t("profile.error.workouts") : null,
  };
  const valid = Object.values(errors).every((error) => error === null);
  const number = (value: number | null | "bad"): number | null => (value === "bad" ? null : value);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setTouched(true);
    if (!valid) return;
    update.mutate(
      {
        username: name.trim(),
        goal: goal || null,
        gender: gender || null,
        age: number(parsed.age),
        height: number(parsed.height),
        weight: number(parsed.weight),
        activity: activity || null,
        experience: experience || null,
        workouts_per_week: number(parsed.workouts),
        training_location: location,
      },
      { onSuccess: onClose },
    );
  };

  const genders: Option<string>[] = options.genders.map((id) => ({ id, label: text.option("genders", id) ?? id }));
  const locations: Option<string>[] = options.locations.map((id) => ({ id, label: t(`profile.location.${id as "gym" | "home" | "outdoor"}`) }));

  return (
    <Sheet open size="lg" onClose={onClose} title={t("profile.edit")}>
      <form onSubmit={submit} noValidate className="space-y-4">
        <TextField label={t("profile.name")} value={name} onChange={(event) => setName(event.target.value)} maxLength={50} autoComplete="nickname" error={touched ? errors.name : null} />

        <SelectField label={t("profile.goal")} value={goal} onChange={(event) => setGoal(event.target.value)}>
          <option value="">{t("profile.notSet")}</option>
          {options.goals.map((id) => (
            <option key={id} value={id}>
              {text.option("goals", id) ?? id}
            </option>
          ))}
        </SelectField>

        <div>
          <p className="mb-1.5 text-sm font-medium text-ink-2">{t("profile.gender")}</p>
          <Chips wrap label={t("profile.gender")} options={genders} value={gender} onChange={setGender} />
        </div>

        <div className="grid grid-cols-3 gap-2">
          <TextField label={t("profile.age")} inputMode="numeric" value={age} onChange={(event) => setAge(event.target.value)} error={touched ? errors.age : null} />
          <TextField label={t("profile.height")} inputMode="decimal" value={height} onChange={(event) => setHeight(event.target.value)} suffix={t("unit.cm")} error={touched ? errors.height : null} />
          <TextField label={t("profile.weight")} inputMode="decimal" value={weight} onChange={(event) => setWeight(event.target.value)} suffix={t("unit.kg")} error={touched ? errors.weight : null} />
        </div>

        <SelectField label={t("profile.activity")} value={activity} onChange={(event) => setActivity(event.target.value)}>
          <option value="">{t("profile.notSet")}</option>
          {options.activities.map(([value, key]) => (
            <option key={value} value={value}>
              {text.option("activity", key) ?? key}
            </option>
          ))}
        </SelectField>

        <div className="grid grid-cols-2 gap-2">
          <SelectField label={t("profile.experience")} value={experience} onChange={(event) => setExperience(event.target.value)}>
            <option value="">{t("profile.notSet")}</option>
            {options.experiences.map((id) => (
              <option key={id} value={id}>
                {text.option("experience", id) ?? id}
              </option>
            ))}
          </SelectField>
          <TextField
            label={t("profile.workouts")}
            inputMode="numeric"
            value={workouts}
            onChange={(event) => setWorkouts(event.target.value)}
            error={touched ? errors.workouts : null}
          />
        </div>

        <div>
          <p className="mb-1.5 text-sm font-medium text-ink-2">{t("profile.location")}</p>
          <Chips wrap label={t("profile.location")} options={locations} value={location} onChange={setLocation} />
        </div>

        {update.isError && (
          <p role="alert" className="text-sm text-error">
            {t("profile.error.save")}
          </p>
        )}
        <Button type="submit" variant="primary" size="lg" block busy={update.isPending}>
          {t("common.save")}
        </Button>
      </form>
    </Sheet>
  );
}
