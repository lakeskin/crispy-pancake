import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  palette: {
    primary: {
      main: "#1565c0",      // Professional blue
      light: "#42a5f5",
      dark: "#0d47a1",
    },
    secondary: {
      main: "#ff8f00",       // Warm amber — mechanic / automotive feel
      light: "#ffc046",
      dark: "#c56000",
    },
    background: {
      default: "#f5f7fa",
      paper: "#ffffff",
    },
    error: { main: "#d32f2f" },
    warning: { main: "#ff9800" },
    success: { main: "#2e7d32" },
  },
  typography: {
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    h4: { fontWeight: 700 },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
  },
  shape: { borderRadius: 12 },
  components: {
    MuiButton: {
      styleOverrides: {
        root: { textTransform: "none", fontWeight: 600, borderRadius: 10, padding: "8px 20px" },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: { borderRadius: 16, boxShadow: "0 2px 12px rgba(0,0,0,0.08)" },
      },
    },
    MuiTextField: {
      defaultProps: { variant: "outlined", size: "small" },
    },
  },
});
