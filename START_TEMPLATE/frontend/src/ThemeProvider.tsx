import { createContext, useContext, useEffect, useState } from 'react';
import { createTheme, ThemeProvider as MUIThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { GlobalStyles } from '@mui/material';
import axios from 'axios';

export interface CustomClass {
    [key: string]: any;
}

export interface CustomClasses {
    buttons: { [key: string]: CustomClass };
    cards: { [key: string]: CustomClass };
    typography: { [key: string]: CustomClass };
    inputs: { [key: string]: CustomClass };
    chips: { [key: string]: CustomClass };
}

export interface ThemeConfig {
    metadata?: {
        name: string;
        version: string;
        lastModified: string;
    };
    customClasses: CustomClasses;
    palette: {
        mode: 'light' | 'dark';
        primary: { main: string };
        secondary: { main: string };
        error: { main: string };
        warning: { main: string };
        info: { main: string };
        success: { main: string };
        background: { default: string; paper: string };
    };
    typography: {
        fontFamily: string;
        fontSize: number;
    };
    shape: { borderRadius: number };
    spacing: number;
}

const defaultConfig: ThemeConfig = {
    customClasses: {
        buttons: {},
        cards: {},
        typography: {},
        inputs: {},
        chips: {}
    },
    palette: {
        mode: 'light',
        primary: { main: '#1976d2' },
        secondary: { main: '#dc004e' },
        error: { main: '#f44336' },
        warning: { main: '#ff9800' },
        info: { main: '#2196f3' },
        success: { main: '#4caf50' },
        background: { default: '#ffffff', paper: '#f5f5f5' },
    },
    typography: {
        fontFamily: 'Roboto, sans-serif',
        fontSize: 14,
    },
    shape: { borderRadius: 4 },
    spacing: 8,
};

const ThemeContext = createContext<{
    config: ThemeConfig;
    updateConfig: (config: ThemeConfig) => void;
    refreshConfig: () => void;
}>({
    config: defaultConfig,
    updateConfig: () => { },
    refreshConfig: () => { },
});

export const useThemeConfig = () => useContext(ThemeContext);

// Generate CSS for custom classes
function generateCustomClassesCSS(customClasses: CustomClasses): string {
    let css = '';

    // Button classes
    Object.entries(customClasses.buttons || {}).forEach(([name, props]) => {
        css += `
      .btn-${name} {
        ${props.variant ? `/* variant: ${props.variant} */` : ''}
        ${props.color ? `background-color: ${props.color} !important;` : ''}
        ${props.textColor ? `color: ${props.textColor} !important;` : ''}
        ${props.fontSize ? `font-size: ${props.fontSize} !important;` : ''}
        ${props.fontWeight ? `font-weight: ${props.fontWeight} !important;` : ''}
        ${props.borderRadius ? `border-radius: ${props.borderRadius} !important;` : ''}
        ${props.padding ? `padding: ${props.padding} !important;` : ''}
        ${props.textTransform ? `text-transform: ${props.textTransform} !important;` : ''}
        ${props.letterSpacing ? `letter-spacing: ${props.letterSpacing} !important;` : ''}
        ${props.elevation ? `box-shadow: 0px ${props.elevation * 2}px ${props.elevation * 4}px rgba(0,0,0,0.${props.elevation * 2}) !important;` : ''}
        ${props.borderColor ? `border: ${props.borderWidth || '1px'} solid ${props.borderColor} !important;` : ''}
        transition: all ${props.animation?.duration || 200}ms ${props.animation?.easing || 'ease-in-out'} !important;
      }
      .btn-${name}:hover {
        ${props.hoverColor ? `background-color: ${props.hoverColor} !important;` : ''}
        ${props.hoverTextColor ? `color: ${props.hoverTextColor} !important;` : ''}
        ${props.hoverBg ? `background-color: ${props.hoverBg} !important;` : ''}
        ${props.animation?.enabled && props.animation?.hoverScale ? `transform: scale(${props.animation.hoverScale}) !important;` : ''}
      }
    `;
    });

    // Card classes
    Object.entries(customClasses.cards || {}).forEach(([name, props]) => {
        css += `
      .card-${name} {
        ${props.borderRadius ? `border-radius: ${props.borderRadius} !important;` : ''}
        ${props.padding ? `padding: ${props.padding} !important;` : ''}
        ${props.backgroundColor ? `background-color: ${props.backgroundColor} !important;` : ''}
        ${props.border ? `border: ${props.border} !important;` : ''}
        ${props.elevation ? `box-shadow: 0px ${props.elevation * 2}px ${props.elevation * 4}px rgba(0,0,0,0.${props.elevation * 2}) !important;` : ''}
        transition: all ${props.animation?.duration || 300}ms ease-in-out !important;
      }
      .card-${name}:hover {
        ${props.hoverElevation ? `box-shadow: 0px ${props.hoverElevation * 2}px ${props.hoverElevation * 4}px rgba(0,0,0,0.${props.hoverElevation * 2}) !important;` : ''}
        ${props.animation?.hoverLift ? `transform: translateY(-4px) !important;` : ''}
      }
    `;
    });

    // Typography classes
    Object.entries(customClasses.typography || {}).forEach(([name, props]) => {
        css += `
      .text-${name} {
        ${props.fontSize ? `font-size: ${props.fontSize} !important;` : ''}
        ${props.fontWeight ? `font-weight: ${props.fontWeight} !important;` : ''}
        ${props.color ? `color: ${props.color} !important;` : ''}
        ${props.lineHeight ? `line-height: ${props.lineHeight} !important;` : ''}
        ${props.letterSpacing ? `letter-spacing: ${props.letterSpacing} !important;` : ''}
        ${props.textTransform ? `text-transform: ${props.textTransform} !important;` : ''}
      }
    `;
    });

    return css;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
    const [config, setConfig] = useState<ThemeConfig>(defaultConfig);

    const refreshConfig = () => {
        axios.get('http://localhost:8000/api/config')
            .then(res => {
                const newConfig = { ...defaultConfig, ...res.data };
                setConfig(newConfig);
            })
            .catch(() => console.log('Using default theme'));
    };

    useEffect(() => {
        refreshConfig();
    }, []);

    const updateConfig = (newConfig: ThemeConfig) => {
        setConfig(newConfig);
        axios.post('http://localhost:8000/api/config', newConfig).catch(console.error);
    };

    const theme = createTheme({
        palette: config.palette,
        typography: config.typography,
        shape: config.shape,
        spacing: config.spacing,
    });

    const customCSS = generateCustomClassesCSS(config.customClasses);

    return (
        <ThemeContext.Provider value={{ config, updateConfig, refreshConfig }}>
            <MUIThemeProvider theme={theme}>
                <CssBaseline />
                <GlobalStyles styles={customCSS} />
                {children}
            </MUIThemeProvider>
        </ThemeContext.Provider>
    );
}
