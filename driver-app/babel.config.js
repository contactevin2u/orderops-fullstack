module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    plugins: [
      ['module-resolver', { root: ['./'], alias: { '@': './' } }],
      // keep this LAST:
      'react-native-reanimated/plugin',
    ],
  };
};
