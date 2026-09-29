import {
translate,
} from "./loader.js";

export {
getLocale,
loadTranslations,
} from "./loader.js";

export type {
Locale,
TranslationMap,
TranslationValue,
} from "./types.js";

export function t(
key: string,
params: Record<string, string | number> = {},
): string {
return translate(
"training",
key,
params,
);
}

export function common_t(
key: string,
params: Record<string, string | number> = {},
): string {
return translate(
"common",
key,
params,
);
}

export function auth_t(
key: string,
params: Record<string, string | number> = {},
): string {
return translate(
"auth",
key,
params,
);
}

export function public_t(
key: string,
params: Record<string, string | number> = {},
): string {
return translate(
"public",
key,
params,
);
}

export function app_t(
key: string,
params: Record<string, string | number> = {},
): string {
return translate(
"app",
key,
params,
);
}

export function dashboard_t(
key: string,
params: Record<string, string | number> = {},
): string {
return translate(
"dashboard",
key,
params,
);
}

export function exercise_t(
slug: string,
): string {
return translate(
"exercises",
`${slug}.name`,
);
}

export function recovery_t(
key: string,
params: Record<string, string | number> = {},
): string {
return translate(
"recovery",
key,
params,
);
}

export function nutrition_t(
key: string,
params: Record<string, string | number> = {},
): string {
return translate(
"nutrition",
key,
params,
);
}

export function profile_t(
key: string,
params: Record<string, string | number> = {},
): string {
return translate(
"profile",
key,
params,
);
}
