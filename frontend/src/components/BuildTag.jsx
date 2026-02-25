/**
 * BuildTag - Visual build/version indicator
 * 
 * Displays a floating badge showing the current build version.
 * Only renders if REACT_APP_BUILD_TAG environment variable is set.
 * 
 * To remove: Delete this file and remove import from App.js
 */

const BuildTag = () => {
  const buildTag = process.env.REACT_APP_BUILD_TAG;
  
  // Don't render if no build tag is set
  if (!buildTag) return null;
  
  return (
    <div
      style={{
        position: 'fixed',
        bottom: '12px',
        right: '12px',
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        color: 'rgba(255, 255, 255, 0.9)',
        fontSize: '11px',
        fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Monaco, Consolas, monospace',
        fontWeight: 500,
        padding: '6px 10px',
        borderRadius: '9999px',
        zIndex: 99999,
        pointerEvents: 'none',
        userSelect: 'none',
        opacity: 0.7,
        letterSpacing: '0.025em',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
      }}
      data-testid="build-tag"
    >
      {buildTag}
    </div>
  );
};

export default BuildTag;
