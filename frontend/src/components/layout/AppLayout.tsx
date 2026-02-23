import { useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  AppBar, Toolbar, Typography, IconButton, Avatar, Box, Drawer,
  List, ListItemButton, ListItemIcon, ListItemText, Badge, Menu, MenuItem,
  useMediaQuery, useTheme, BottomNavigation, BottomNavigationAction, Paper,
} from "@mui/material";
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  AddCircle as AddIcon,
  Search as SearchIcon,
  Chat as ChatIcon,
  Person as PersonIcon,
  Logout as LogoutIcon,
  Notifications as NotifIcon,
} from "@mui/icons-material";
import { useAuth } from "../../contexts/AuthContext";

const DRAWER_WIDTH = 240;

export default function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const isMechanic = user?.role === "mechanic";

  const navItems = [
    { label: "Dashboard", icon: <DashboardIcon />, path: "/dashboard" },
    ...(isMechanic
      ? [{ label: "Issue Feed", icon: <SearchIcon />, path: "/feed" }]
      : [{ label: "New Issue", icon: <AddIcon />, path: "/issues/new" }]),
    { label: "Conversations", icon: <ChatIcon />, path: "/conversations" },
    { label: "Profile", icon: <PersonIcon />, path: "/profile" },
  ];

  const bottomNavValue = navItems.findIndex((n) => location.pathname.startsWith(n.path));

  const drawer = (
    <Box sx={{ width: DRAWER_WIDTH, pt: 2 }}>
      <Box sx={{ px: 2, mb: 2 }}>
        <Typography variant="h6" fontWeight={700} color="primary">
          🚗 SalikChat
        </Typography>
      </Box>
      <List>
        {navItems.map((item) => (
          <ListItemButton
            key={item.path}
            selected={location.pathname.startsWith(item.path)}
            onClick={() => { navigate(item.path); setDrawerOpen(false); }}
          >
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
      {/* Desktop sidebar */}
      {!isMobile && (
        <Drawer variant="permanent" sx={{
          width: DRAWER_WIDTH,
          "& .MuiDrawer-paper": { width: DRAWER_WIDTH, borderRight: "1px solid #e0e0e0" },
        }}>
          {drawer}
        </Drawer>
      )}

      {/* Mobile drawer */}
      {isMobile && (
        <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)}>
          {drawer}
        </Drawer>
      )}

      {/* Main content area */}
      <Box sx={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        {/* Top bar */}
        <AppBar position="sticky" color="inherit" elevation={1} sx={{ bgcolor: "white" }}>
          <Toolbar>
            {isMobile && (
              <IconButton edge="start" onClick={() => setDrawerOpen(true)} sx={{ mr: 1 }}>
                <MenuIcon />
              </IconButton>
            )}
            <Typography variant="h6" fontWeight={700} color="primary" sx={{ flex: 1 }}>
              {isMobile ? "🚗 SalikChat" : ""}
            </Typography>

            <IconButton>
              <Badge badgeContent={0} color="error">
                <NotifIcon />
              </Badge>
            </IconButton>

            <IconButton onClick={(e) => setAnchorEl(e.currentTarget)}>
              <Avatar sx={{ width: 34, height: 34, bgcolor: "primary.main", fontSize: 14 }}>
                {user?.full_name?.charAt(0).toUpperCase() || "U"}
              </Avatar>
            </IconButton>

            <Menu anchorEl={anchorEl} open={!!anchorEl} onClose={() => setAnchorEl(null)}>
              <MenuItem disabled>
                <Typography variant="body2">{user?.email}</Typography>
              </MenuItem>
              <MenuItem onClick={() => { setAnchorEl(null); navigate("/profile"); }}>
                <PersonIcon fontSize="small" sx={{ mr: 1 }} /> Profile
              </MenuItem>
              <MenuItem onClick={() => { setAnchorEl(null); logout(); navigate("/"); }}>
                <LogoutIcon fontSize="small" sx={{ mr: 1 }} /> Logout
              </MenuItem>
            </Menu>
          </Toolbar>
        </AppBar>

        {/* Page content */}
        <Box sx={{ flex: 1, p: { xs: 2, md: 3 }, pb: isMobile ? 10 : 3, overflowY: "auto" }}>
          <Outlet />
        </Box>

        {/* Mobile bottom nav */}
        {isMobile && (
          <Paper sx={{ position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 1200 }} elevation={3}>
            <BottomNavigation
              value={bottomNavValue >= 0 ? bottomNavValue : 0}
              onChange={(_, idx) => navigate(navItems[idx].path)}
              showLabels
            >
              {navItems.map((item) => (
                <BottomNavigationAction key={item.path} label={item.label} icon={item.icon} />
              ))}
            </BottomNavigation>
          </Paper>
        )}
      </Box>
    </Box>
  );
}
