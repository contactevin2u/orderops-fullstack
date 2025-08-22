import { useTranslation } from 'react-i18next';

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();
  return (
    <select
      className="border border-ink-200 rounded-lg p-2 bg-white text-ink-900"
      value={i18n.language}
      onChange={(e) => i18n.changeLanguage(e.target.value)}
    >
      <option value="en">EN</option>
      <option value="ms">BM</option>
      <option value="zh">中文</option>
    </select>
  );
}
