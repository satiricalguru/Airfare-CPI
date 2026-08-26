import "./globals.css";

export const metadata = {
  title: "Airfare CPI — Real-Time Airfare Price Index | SIH26056",
  description:
    "Real-Time Airfare Price Index for India — Automated web scraping of airline and OTA portals for CPI augmentation. MoSPI SIH26056.",
  keywords: "airfare, CPI, price index, MoSPI, India, aviation, inflation",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
