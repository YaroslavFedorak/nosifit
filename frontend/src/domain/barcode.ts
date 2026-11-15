function checkDigit(body: string): number {
  let total = 0;
  for (let index = 0; index < body.length; index += 1) {
    const digit = Number(body[body.length - 1 - index]);
    total += digit * (index % 2 === 0 ? 3 : 1);
  }
  return (10 - (total % 10)) % 10;
}

/** Digits of a retail barcode with a valid check digit, else null. */
export function cleanBarcode(raw: string): string | null {
  const code = raw.replace(/[\s-]+/g, "");
  if (!/^\d+$/.test(code) || ![8, 12, 13, 14].includes(code.length)) return null;
  return checkDigit(code.slice(0, -1)) === Number(code[code.length - 1]) ? code : null;
}

/** UPC-E (8 digits) is a compressed UPC-A; the product database knows the long form. */
export function expandUpcE(code: string): string {
  if (!/^\d{8}$/.test(code)) return code;
  const system = code[0] ?? "";
  const body = code.slice(1, 7);
  const check = code[7] ?? "";
  const last = body[5] ?? "";
  let middle: string;
  if ("012".includes(last)) middle = body.slice(0, 2) + last + "0000" + body.slice(2, 5);
  else if (last === "3") middle = body.slice(0, 3) + "00000" + body.slice(3, 5);
  else if (last === "4") middle = body.slice(0, 4) + "00000" + body[4];
  else middle = body.slice(0, 5) + "0000" + last;
  return system + middle + check;
}
