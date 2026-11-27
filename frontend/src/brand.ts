// The brand marks of web/app/static/img/brand, built into the bundle: they
// get the bundle's versioned, cached-for-a-year address instead of a plain
// /static/... one that the browser has to check again on every visit.
import lockup from "../../web/app/static/img/brand/nosifit-lockup-on-dark.svg";
import mark from "../../web/app/static/img/brand/nosifit-mark-on-dark.svg";

export const brand = { mark, lockup } as const;
