/** Vite turns an imported image into its URL (or a data: URL when it is small). */
declare module "*.svg" {
  const url: string;
  export default url;
}
