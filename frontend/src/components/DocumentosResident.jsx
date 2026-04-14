import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { toast } from 'sonner';
import api from '../services/api';
import {
  Download,
  FolderOpen,
  FileText,
  File,
  Image,
  FileSpreadsheet,
  Loader2,
  Filter,
} from 'lucide-react';

const CATEGORY_LABELS = {
  reglamento: 'Reglamento',
  acta: 'Acta',
  comunicado: 'Comunicado',
  contrato: 'Contrato',
  manual: 'Manual',
  financiero: 'Financiero',
  otro: 'Otro',
};

const FILE_ICONS = {
  'application/pdf': FileText,
  'image/jpeg': Image,
  'image/png': Image,
  'text/csv': FileSpreadsheet,
};

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentosResident() {
  const { t } = useTranslation();
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterCategory, setFilterCategory] = useState('all');
  const [downloading, setDownloading] = useState(null);

  const fetchDocs = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page_size: 50 };
      if (filterCategory !== 'all') params.category = filterCategory;
      const data = await api.getDocuments(params);
      setDocs(data.items || []);
    } catch {
      setDocs([]);
    } finally {
      setLoading(false);
    }
  }, [filterCategory]);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  const handleDownload = async (doc) => {
    setDownloading(doc.id);
    try {
      await api.downloadDocument(doc.id, doc.file_name);
    } catch (err) {
      toast.error(err.message || 'Error al descargar');
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="h-full overflow-y-auto" style={{ WebkitOverflowScrolling: 'touch', paddingBottom: '112px' }}>
      <div className="p-3 space-y-4" data-testid="documentos-resident">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">{t('documentos.title', 'Documentos')}</h2>
          <Select value={filterCategory} onValueChange={setFilterCategory}>
            <SelectTrigger data-testid="resident-doc-filter" className="h-8 w-32 bg-[#181B25] border-[#1E293B] text-xs">
              <Filter className="w-3 h-3 mr-1" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#0F111A] border-[#1E293B]">
              <SelectItem value="all">Todas</SelectItem>
              {Object.entries(CATEGORY_LABELS).map(([k, v]) => (
                <SelectItem key={k} value={k}>{v}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        ) : docs.length === 0 ? (
          <Card className="bg-[#0F111A] border-[#1E293B]">
            <CardContent className="p-6 text-center">
              <FolderOpen className="w-10 h-10 text-muted-foreground/30 mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">{t('documentos.noDocs', 'No hay documentos disponibles')}</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2">
            {docs.map((doc) => {
              const Icon = FILE_ICONS[doc.file_type] || File;
              return (
                <Card
                  key={doc.id}
                  className="bg-[#0F111A] border-[#1E293B]"
                  data-testid={`resident-doc-${doc.id}`}
                >
                  <CardContent className="p-3 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <Icon className="w-5 h-5 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-medium text-white truncate">{doc.name}</h4>
                      <div className="flex items-center gap-2 mt-0.5">
                        <Badge variant="outline" className="text-[10px] h-4 bg-[#0F111A] text-muted-foreground border-[#1E293B]">
                          {CATEGORY_LABELS[doc.category] || doc.category}
                        </Badge>
                        <span className="text-[10px] text-muted-foreground">{formatSize(doc.file_size)}</span>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-9 w-9 p-0 flex-shrink-0"
                      onClick={() => handleDownload(doc)}
                      disabled={downloading === doc.id}
                      data-testid={`resident-download-${doc.id}`}
                    >
                      {downloading === doc.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
