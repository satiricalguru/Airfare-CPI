import "./globals.css";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

export const metadata = {
  title: "Airfare CPI — Real-Time Aviation Price Intelligence",
  description:
    "Ministry of Statistics & Programme Implementation (MoSPI) Real-Time Airfare Price Index for India — Automated web scraping of airline and OTA portals for CPI augmentation.",
  keywords: "Airfare CPI, price index, MoSPI, India, aviation, inflation, statistics, SIH26056",
  icons: {
    icon: `${basePath}/favicon.png?v=2`,
    shortcut: `${basePath}/favicon.ico?v=2`,
    apple: `${basePath}/apple-touch-icon.png?v=2`,
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="light" suppressHydrationWarning>
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
          rel="stylesheet"
        />
        <link rel="icon" type="image/png" sizes="32x32" href={`${basePath}/favicon-32x32.png?v=2`} />
        <link rel="icon" type="image/png" sizes="192x192" href={`${basePath}/favicon.png?v=2`} />
        <link rel="icon" type="image/x-icon" href={`${basePath}/favicon.ico?v=2`} />
        <link rel="shortcut icon" href={`${basePath}/favicon.ico?v=2`} />
        <link rel="apple-touch-icon" sizes="180x180" href={`${basePath}/apple-touch-icon.png?v=2`} />
      </head>
      <body className="antialiased" suppressHydrationWarning>{children}</body>
    </html>
  );
}
