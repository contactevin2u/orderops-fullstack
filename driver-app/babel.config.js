module.exports = function (api) {
  api.cache(true);
  const plugins = [
    ['module-resolver', { root: ['./'], alias: { '@': './' } }],
  ];
  // Include Reanimated plugin only if installed; keep it LAST.
  try {
    require.resolve('react-native-reanimated/package.json');
    plugins.push('react-native-reanimated/plugin');
  } catch {}
  return { presets: ['babel-preset-expo'], plugins };
};
