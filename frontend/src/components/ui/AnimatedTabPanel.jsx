/**
 * GENTURIX - Animated Tab Panel
 * 
 * Provides smooth horizontal slide transitions between tab panels.
 * Uses Framer Motion for premium, fast animations.
 * 
 * Features:
 * - Horizontal carousel-like slide effect
 * - Direction-aware animation (left/right based on tab order)
 * - No layout shift or scroll jump
 * - Instant data rendering (animation doesn't block content)
 * - 250ms duration for premium feel
 */

import React, { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// Tab order for determining slide direction
const DEFAULT_TAB_ORDER = ['emergency', 'visits', 'reservations', 'directory', 'profile'];

/**
 * Determines the slide direction based on previous and current tab
 * @returns 1 for right-to-left (next), -1 for left-to-right (prev)
 */
const getDirection = (prevTab, currentTab, tabOrder = DEFAULT_TAB_ORDER) => {
  const prevIndex = tabOrder.indexOf(prevTab);
  const currentIndex = tabOrder.indexOf(currentTab);
  
  if (prevIndex === -1 || currentIndex === -1) return 1;
  return currentIndex > prevIndex ? 1 : -1;
};

// Animation variants for slide effect
const slideVariants = {
  enter: (direction) => ({
    x: direction > 0 ? '30%' : '-30%',
    opacity: 0,
  }),
  center: {
    x: 0,
    opacity: 1,
  },
  exit: (direction) => ({
    x: direction > 0 ? '-30%' : '30%',
    opacity: 0,
  }),
};

// Transition config - fast and premium
const slideTransition = {
  type: 'tween',
  ease: [0.32, 0.72, 0, 1], // Custom ease for premium feel
  duration: 0.25, // 250ms
};

/**
 * AnimatedTabPanel - Wrapper for tab content with slide animations
 * 
 * @param {string} activeTab - Currently active tab key
 * @param {React.ReactNode} children - Tab content to render
 * @param {string[]} tabOrder - Order of tabs for direction calculation
 * @param {string} className - Additional CSS classes
 */
export const AnimatedTabPanel = ({ 
  activeTab, 
  children, 
  tabOrder = DEFAULT_TAB_ORDER,
  className = '' 
}) => {
  const prevTabRef = useRef(activeTab);
  const direction = getDirection(prevTabRef.current, activeTab, tabOrder);
  
  // Update previous tab after render
  useEffect(() => {
    prevTabRef.current = activeTab;
  }, [activeTab]);

  return (
    <div className={`relative overflow-hidden ${className}`}>
      <AnimatePresence initial={false} mode="wait" custom={direction}>
        <motion.div
          key={activeTab}
          custom={direction}
          variants={slideVariants}
          initial="enter"
          animate="center"
          exit="exit"
          transition={slideTransition}
          className="w-full"
        >
          {children}
        </motion.div>
      </AnimatePresence>
    </div>
  );
};

/**
 * AnimatedTabContent - Individual tab panel with animation
 * Use this when you need more control over each tab's animation
 * 
 * @param {boolean} isActive - Whether this tab is currently active
 * @param {number} direction - Animation direction (-1 or 1)
 * @param {React.ReactNode} children - Content to render
 */
export const AnimatedTabContent = ({ 
  isActive, 
  direction = 1, 
  children,
  className = '' 
}) => {
  if (!isActive) return null;
  
  return (
    <motion.div
      initial="enter"
      animate="center"
      exit="exit"
      custom={direction}
      variants={slideVariants}
      transition={slideTransition}
      className={className}
    >
      {children}
    </motion.div>
  );
};

export default AnimatedTabPanel;
