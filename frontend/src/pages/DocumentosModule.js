import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { toast } from 'sonner';
import api from '../services/api';
import {
  Upload,
  FileText,
  Download,
  Trash2,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Filter,
  FolderOpen,
  File,
  Image,
  FileSpreadsheet,
  Pencil,
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

const VISIBILITY_LABELS = {
  public: 'Público',
  private: 'Privado',
  roles: 'Por roles',
};

const FILE_ICONS = {
  'application/pdf': FileText,
  'image/jpeg': Image,
  'image/png': Image,
  'image/gif': Image,
  'image/webp': Image,
  'text/plain': File,
  'text/csv': FileSpreadsheet,
};

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileIcon(type) {
  const Icon = FILE_ICONS[type] || File;
  return Icon;
}

// ── Upload Dialog ──
const UploadDialog = ({ open, onClose, onUploaded }) => {
  const { t } = useTranslation();
  const fileRef = useRef(null);
  const [file, setFile] = useState(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('otro');
  const [visibility, setVisibility] = useState('public');
  const [allowedRoles, setAllowedRoles] = useState([]);
  const [uploading, setUploading] = useState(false);

  const roles = ['Residente', 'Guarda', 'Supervisor', 'Administrador'];

  const toggleRole = (role) => {
    setAllowedRoles((prev) =>
      prev.includes(role) ? prev.filter((r) => r !== role) : [...prev, role]
    );
  };

  const handleFileChange = (e) => {
    const f = e.target.files?.[0];
    if (f) {
      setFile(f);
      if (!name) setName(f.name.replace(/\.[^.]+$/, ''));
    }
  };

  const handleSubmit = async () => {
    if (!file || !name.trim()) {
      toast.error(t('documentos.fillRequired', 'Selecciona un archivo y nombre'));
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      toast.error(t('documentos.tooLarge', 'Archivo excede 20 MB'));
      return;
    }
    setUploading(true);
    try {
      await api.uploadDocument(file, {
        name: name.trim(),
        description: description.trim(),
        category,
        visibility,
        allowed_roles: allowedRoles.join(','),
      });
      toast.success(t('documentos.uploaded', 'Documento subido'));
      setFile(null);
      setName('');
      setDescription('');
      setCategory('otro');
      setVisibility('public');
      setAllowedRoles([]);
      onUploaded?.();
      onClose();
    } catch (err) {
      toast.error(err.message || 'Error al subir');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-lg" data-testid="upload-doc-dialog">
        <DialogHeader>
          <DialogTitle>{t('documentos.upload', 'Subir Documento')}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Archivo *</label>
            <div
              onClick={() => fileRef.current?.click()}
              className="border-2 border-dashed border-[#1E293B] rounded-lg p-6 text-center cursor-pointer hover:border-primary/50 transition-colors"
              data-testid="file-drop-zone"
            >
              <Upload className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
              {file ? (
                <p className="text-sm text-white">{file.name} ({formatSize(file.size)})</p>
              ) : (
                <p className="text-sm text-muted-foreground">Haz clic para seleccionar archivo (max 20 MB)</p>
              )}
            </div>
            <input ref={fileRef} type="file" className="absolute w-0 h-0 opacity-0 overflow-hidden" onChange={handleFileChange} data-testid="file-input" />
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Nombre *</label>
            <Input
              data-testid="doc-name-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={200}
              className="bg-[#181B25] border-[#1E293B]"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Descripción</label>
            <textarea
              data-testid="doc-description-input"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={2000}
              rows={2}
              className="w-full rounded-md bg-[#181B25] border border-[#1E293B] text-sm px-3 py-2 text-white placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-none"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Categoría</label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger data-testid="doc-category-select" className="bg-[#181B25] border-[#1E293B]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  {Object.entries(CATEGORY_LABELS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Visibilidad</label>
              <Select value={visibility} onValueChange={setVisibility}>
                <SelectTrigger data-testid="doc-visibility-select" className="bg-[#181B25] border-[#1E293B]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  <SelectItem value="public">Público</SelectItem>
                  <SelectItem value="private">Privado (solo admin)</SelectItem>
                  <SelectItem value="roles">Por roles</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          {visibility === 'roles' && (
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Roles con acceso</label>
              <div className="flex flex-wrap gap-2">
                {roles.map((r) => (
                  <button
                    type="button"
                    key={r}
                    onClick={() => toggleRole(r)}
                    className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                      allowedRoles.includes(r)
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-[#181B25] text-muted-foreground border border-[#1E293B]'
                    }`}
                    data-testid={`role-chip-${r}`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>
          )}
          <Button
            onClick={handleSubmit}
            disabled={uploading || !file || !name.trim()}
            data-testid="submit-upload-btn"
            className="w-full"
          >
            {uploading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Upload className="w-4 h-4 mr-2" />}
            {t('documentos.uploadBtn', 'Subir Documento')}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// ── Main Page ──
export default function DocumentosModule() {
  const { t } = useTranslation();
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filterCategory, setFilterCategory] = useState('all');
  const [showUpload, setShowUpload] = useState(false);
  const [downloading, setDownloading] = useState(null);
  const [deleting, setDeleting] = useState(null);

  const fetchDocs = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, page_size: 15 };
      if (filterCategory !== 'all') params.category = filterCategory;
      const data = await api.getDocuments(params);
      setDocs(data.items || []);
      setTotalPages(data.total_pages || 1);
    } catch {
      setDocs([]);
    } finally {
      setLoading(false);
    }
  }, [page, filterCategory]);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  const handleDownload = async (doc) => {
    setDownloading(doc.id);
    try {
      await api.downloadDocument(doc.id, doc.file_name);
      toast.success('Descargando...');
    } catch (err) {
      toast.error(err.message || 'Error al descargar');
    } finally {
      setDownloading(null);
    }
  };

  const handleDelete = async (doc) => {
    if (!window.confirm(`¿Eliminar "${doc.name}"?`)) return;
    setDeleting(doc.id);
    try {
      await api.deleteDocument(doc.id);
      toast.success('Documento eliminado');
      fetchDocs();
    } catch (err) {
      toast.error(err.message || 'Error');
    } finally {
      setDeleting(null);
    }
  };

  return (
    <DashboardLayout title={t('documentos.pageTitle', 'Documentos')}>
      <div data-testid="documentos-module" className="space-y-6">
        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base">
                <FolderOpen className="w-4 h-4 text-primary" />
                {t('documentos.list', 'Documentos del Condominio')}
              </CardTitle>
              <div className="flex items-center gap-2">
                <Select value={filterCategory} onValueChange={(v) => { setFilterCategory(v); setPage(1); }}>
                  <SelectTrigger data-testid="filter-category" className="h-8 w-32 bg-[#181B25] border-[#1E293B] text-xs">
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
                <Button size="sm" onClick={() => setShowUpload(true)} data-testid="upload-btn">
                  <Upload className="w-4 h-4 mr-1" />
                  Subir
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
              </div>
            ) : docs.length === 0 ? (
              <div className="text-center py-8">
                <FolderOpen className="w-10 h-10 text-muted-foreground/30 mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">No hay documentos</p>
                <Button size="sm" className="mt-3" onClick={() => setShowUpload(true)} data-testid="empty-upload-btn">
                  <Upload className="w-4 h-4 mr-1" /> Subir primer documento
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                {docs.map((doc) => {
                  const Icon = getFileIcon(doc.file_type);
                  return (
                    <div
                      key={doc.id}
                      data-testid={`doc-row-${doc.id}`}
                      className="p-3 rounded-lg bg-[#181B25] border border-[#1E293B]/50 flex items-center gap-3"
                    >
                      <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <Icon className="w-5 h-5 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-medium text-white truncate">{doc.name}</h4>
                        <div className="flex items-center gap-2 mt-0.5">
                          <Badge variant="outline" className="text-[10px] h-4 bg-[#0F111A] text-muted-foreground border-[#1E293B]">
                            {CATEGORY_LABELS[doc.category] || doc.category}
                          </Badge>
                          <Badge variant="outline" className="text-[10px] h-4 bg-[#0F111A] text-muted-foreground border-[#1E293B]">
                            {VISIBILITY_LABELS[doc.visibility] || doc.visibility}
                          </Badge>
                          <span className="text-[10px] text-muted-foreground">{formatSize(doc.file_size)}</span>
                          <span className="text-[10px] text-muted-foreground">
                            {new Date(doc.created_at).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' })}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0"
                          onClick={() => handleDownload(doc)}
                          disabled={downloading === doc.id}
                          data-testid={`download-${doc.id}`}
                        >
                          {downloading === doc.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0 text-red-400 hover:text-red-300"
                          onClick={() => handleDelete(doc)}
                          disabled={deleting === doc.id}
                          data-testid={`delete-${doc.id}`}
                        >
                          {deleting === doc.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-4">
                <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)} data-testid="docs-prev-page">
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <span className="text-xs text-muted-foreground">{page} / {totalPages}</span>
                <Button variant="ghost" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)} data-testid="docs-next-page">
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        <UploadDialog open={showUpload} onClose={() => setShowUpload(false)} onUploaded={fetchDocs} />
      </div>
    </DashboardLayout>
  );
}
