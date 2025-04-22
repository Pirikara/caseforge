"use client"

import * as React from 'react';
import { Header as HeaderComponent } from './organisms/Header';
import { Sidebar as SidebarComponent } from './organisms/Sidebar';
import { Footer as FooterComponent } from './organisms/Footer';

// メモ化されたコンポーネント
export const Header = React.memo(HeaderComponent);
export const Sidebar = React.memo(SidebarComponent);
export const Footer = React.memo(FooterComponent);