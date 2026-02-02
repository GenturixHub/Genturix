/**
 * GENTURIX - Language Selector Component
 * Allows users to change their preferred language
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Loader2, Globe, Check } from 'lucide-react';
import { changeLanguage, availableLanguages, getCurrentLanguage } from '../i18n';
import api from '../services/api';
import { toast } from 'sonner';

const LanguageSelector = ({ onLanguageChange }) => {
  const { t } = useTranslation();
  const [isUpdating, setIsUpdating] = useState(false);
  const [currentLang, setCurrentLang] = useState(getCurrentLanguage());

  const handleLanguageChange = async (langCode) => {
    if (langCode === currentLang) return;
    
    setIsUpdating(true);
    
    try {
      // Update in backend
      await api.updateLanguage(langCode);
      
      // Update in frontend (i18n + localStorage)
      await changeLanguage(langCode);
      setCurrentLang(langCode);
      
      // Notify parent component if callback provided
      if (onLanguageChange) {
        onLanguageChange(langCode);
      }
      
      toast.success(t('profile.languageUpdated'));
    } catch (error) {
      console.error('Error updating language:', error);
      toast.error(t('errors.generic'));
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <Card className="bg-[#0F111A] border-[#1E293B]">
      <CardHeader className="p-3 pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Globe className="w-4 h-4" />
          {t('profile.language')}
        </CardTitle>
        <CardDescription className="text-xs">
          {t('profile.languageHint')}
        </CardDescription>
      </CardHeader>
      <CardContent className="p-3 pt-0">
        <div className="flex gap-2 flex-wrap">
          {availableLanguages.map((lang) => {
            const isActive = lang.code === currentLang;
            
            return (
              <Button
                key={lang.code}
                variant={isActive ? "default" : "outline"}
                size="sm"
                onClick={() => handleLanguageChange(lang.code)}
                disabled={isUpdating}
                className={`
                  relative min-w-[100px]
                  ${isActive 
                    ? 'bg-primary text-primary-foreground' 
                    : 'bg-[#0A0A0F] border-[#1E293B] hover:bg-[#1E293B]'
                  }
                `}
                data-testid={`language-btn-${lang.code}`}
              >
                {isUpdating && lang.code !== currentLang ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-1" />
                ) : (
                  <span className="mr-2">{lang.flag}</span>
                )}
                {lang.name}
                {isActive && (
                  <Check className="w-3 h-3 ml-1" />
                )}
              </Button>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
};

export default LanguageSelector;
