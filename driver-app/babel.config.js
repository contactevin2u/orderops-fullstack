module.exports = function (api) {
  api.cache(true);
  const plugins = [
    ['module-resolver', { root: ['./'], alias: { '@': './' } }],
  ];
  try { require.resolve('react-native-reanimated/package.json'); plugins.push('react-native-reanimated/plugin'); } catch {}
  return { presets: ['babel-preset-expo'], plugins };
};
