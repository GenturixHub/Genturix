import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, FileText, Users, Shield, Building, Server, AlertTriangle, Mail } from 'lucide-react';

const TermsOfServicePage = () => {
  useEffect(() => {
    document.title = 'Terms of Service | Genturix';
    // Add meta description
    const metaDescription = document.querySelector('meta[name="description"]');
    if (metaDescription) {
      metaDescription.setAttribute('content', 'Genturix Terms of Service - Read our terms and conditions for using the condominium security management platform.');
    }
    // Scroll to top on mount
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="min-h-screen bg-[#0f172a] text-gray-200">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-[#0f172a]/95 backdrop-blur-sm border-b border-[#1e293b]">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4">
          <Link 
            to="/login" 
            className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            <span className="text-sm">Volver</span>
          </Link>
          <div className="flex-1 text-center">
            <h1 className="text-lg font-semibold text-white">GENTURIX</h1>
          </div>
          <div className="w-20" /> {/* Spacer for centering */}
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 py-8 pb-20">
        <div className="space-y-8">
          {/* Title */}
          <div className="text-center space-y-2">
            <FileText className="w-12 h-12 mx-auto text-blue-400" />
            <h1 className="text-3xl font-bold text-white">Términos de Servicio</h1>
            <p className="text-gray-400">Última actualización: Marzo 2026</p>
          </div>

          {/* Section 1: Acceptance of Terms */}
          <section className="bg-[#1e293b] rounded-xl p-6 space-y-4">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <span className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center text-blue-400">1</span>
              Aceptación de Términos
            </h2>
            <p className="text-gray-300 leading-relaxed">
              Al acceder o utilizar Genturix, usted acepta estar sujeto a estos Términos de Servicio y a nuestra 
              Política de Privacidad. Si no está de acuerdo con alguna parte de estos términos, no podrá acceder 
              al servicio.
            </p>
            <div className="bg-[#0f172a] rounded-lg p-4 border-l-4 border-blue-500">
              <p className="text-gray-300 text-sm">
                <strong className="text-white">Importante:</strong> Estos términos constituyen un acuerdo legal 
                vinculante entre usted y Genturix. Le recomendamos leerlos detenidamente.
              </p>
            </div>
          </section>

          {/* Section 2: User Responsibilities */}
          <section className="bg-[#1e293b] rounded-xl p-6 space-y-4">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <span className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center text-blue-400">2</span>
              <Users className="w-5 h-5" />
              Responsabilidades del Usuario
            </h2>
            <p className="text-gray-300 leading-relaxed">
              Como usuario de Genturix, usted se compromete a:
            </p>
            <ul className="text-gray-300 space-y-3">
              <li className="flex items-start gap-3">
                <span className="w-6 h-6 bg-green-500/20 rounded-full flex items-center justify-center text-green-400 text-sm flex-shrink-0 mt-0.5">✓</span>
                <span>Proporcionar información veraz y actualizada durante el registro y uso de la plataforma.</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="w-6 h-6 bg-green-500/20 rounded-full flex items-center justify-center text-green-400 text-sm flex-shrink-0 mt-0.5">✓</span>
                <span>Mantener la confidencialidad de sus credenciales de acceso y no compartirlas con terceros.</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="w-6 h-6 bg-green-500/20 rounded-full flex items-center justify-center text-green-400 text-sm flex-shrink-0 mt-0.5">✓</span>
                <span>Utilizar el sistema de autorización de visitantes de manera responsable y veraz.</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="w-6 h-6 bg-green-500/20 rounded-full flex items-center justify-center text-green-400 text-sm flex-shrink-0 mt-0.5">✓</span>
                <span>No utilizar el sistema de pánico de manera fraudulenta o para fines no autorizados.</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="w-6 h-6 bg-green-500/20 rounded-full flex items-center justify-center text-green-400 text-sm flex-shrink-0 mt-0.5">✓</span>
                <span>Respetar las normas del condominio y las políticas establecidas por la administración.</span>
              </li>
            </ul>
          </section>

          {/* Section 3: Visitor Authorization System */}
          <section className="bg-[#1e293b] rounded-xl p-6 space-y-4">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <span className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center text-blue-400">3</span>
              Sistema de Autorización de Visitantes
            </h2>
            <p className="text-gray-300 leading-relaxed">
              El sistema de autorización de visitantes está diseñado para facilitar el control de acceso al condominio:
            </p>
            <div className="space-y-3 mt-4">
              <div className="bg-[#0f172a] rounded-lg p-4">
                <h3 className="font-medium text-white mb-2">Para Residentes</h3>
                <ul className="text-gray-300 text-sm space-y-1">
                  <li>• Puede pre-registrar visitantes con anticipación</li>
                  <li>• Puede crear autorizaciones de un solo uso o recurrentes</li>
                  <li>• Es responsable de los visitantes que autorice</li>
                  <li>• Recibirá notificaciones cuando sus visitantes lleguen</li>
                </ul>
              </div>
              <div className="bg-[#0f172a] rounded-lg p-4">
                <h3 className="font-medium text-white mb-2">Para Guardias</h3>
                <ul className="text-gray-300 text-sm space-y-1">
                  <li>• Debe verificar la identidad de los visitantes</li>
                  <li>• Debe registrar la entrada y salida de visitantes</li>
                  <li>• Puede contactar al residente para confirmar autorizaciones</li>
                  <li>• Debe reportar cualquier incidente de seguridad</li>
                </ul>
              </div>
            </div>
          </section>

          {/* Section 4: Security System Usage */}
          <section className="bg-[#1e293b] rounded-xl p-6 space-y-4">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <span className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center text-blue-400">4</span>
              <Shield className="w-5 h-5" />
              Uso del Sistema de Seguridad
            </h2>
            <p className="text-gray-300 leading-relaxed">
              Genturix incluye funciones de seguridad que deben utilizarse de manera responsable:
            </p>
            
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 mt-4">
              <h3 className="font-medium text-red-400 flex items-center gap-2 mb-2">
                <AlertTriangle className="w-5 h-5" />
                Botón de Pánico
              </h3>
              <ul className="text-gray-300 text-sm space-y-1">
                <li>• Solo debe activarse en situaciones de emergencia real</li>
                <li>• El uso indebido puede resultar en la suspensión de su cuenta</li>
                <li>• Las alertas falsas pueden tener consecuencias legales</li>
                <li>• Todas las activaciones quedan registradas en el sistema de auditoría</li>
              </ul>
            </div>

            <div className="bg-[#0f172a] rounded-lg p-4 mt-4">
              <h3 className="font-medium text-white mb-2">Registro de Actividades</h3>
              <p className="text-gray-300 text-sm">
                Todas las acciones realizadas en el sistema (autorizaciones, entradas, salidas, alertas) 
                quedan registradas para propósitos de seguridad y auditoría. Esta información puede ser 
                utilizada por la administración del condominio y, si es necesario, por autoridades competentes.
              </p>
            </div>
          </section>

          {/* Section 5: Condominium Management Responsibilities */}
          <section className="bg-[#1e293b] rounded-xl p-6 space-y-4">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <span className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center text-blue-400">5</span>
              <Building className="w-5 h-5" />
              Responsabilidades de la Administración
            </h2>
            <p className="text-gray-300 leading-relaxed">
              La administración del condominio que contrata Genturix es responsable de:
            </p>
            <ul className="text-gray-300 space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">•</span>
                <span>Gestionar las cuentas de usuarios (residentes, guardias, administradores)</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">•</span>
                <span>Configurar las políticas de seguridad del condominio</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">•</span>
                <span>Supervisar el uso adecuado del sistema por parte de los usuarios</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">•</span>
                <span>Mantener actualizada la información de áreas comunes y configuraciones</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">•</span>
                <span>Responder a incidentes de seguridad reportados a través del sistema</span>
              </li>
            </ul>
          </section>

          {/* Section 6: Service Availability */}
          <section className="bg-[#1e293b] rounded-xl p-6 space-y-4">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <span className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center text-blue-400">6</span>
              <Server className="w-5 h-5" />
              Disponibilidad del Servicio
            </h2>
            <p className="text-gray-300 leading-relaxed">
              Nos esforzamos por mantener Genturix disponible las 24 horas del día, los 7 días de la semana. 
              Sin embargo:
            </p>
            <ul className="text-gray-300 space-y-2 mt-4">
              <li className="flex items-start gap-2">
                <span className="text-yellow-400 mt-1">⚠</span>
                <span>Pueden ocurrir interrupciones por mantenimiento programado</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-yellow-400 mt-1">⚠</span>
                <span>Eventos fuera de nuestro control pueden afectar la disponibilidad</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-yellow-400 mt-1">⚠</span>
                <span>Las notificaciones push dependen de servicios de terceros y conectividad del dispositivo</span>
              </li>
            </ul>
            <div className="bg-[#0f172a] rounded-lg p-4 mt-4">
              <p className="text-gray-400 text-sm">
                <strong className="text-gray-300">Nota:</strong> Genturix no debe ser el único sistema de seguridad 
                del condominio. Recomendamos mantener procedimientos de respaldo para situaciones de emergencia.
              </p>
            </div>
          </section>

          {/* Section 7: Limitation of Liability */}
          <section className="bg-[#1e293b] rounded-xl p-6 space-y-4">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <span className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center text-blue-400">7</span>
              <AlertTriangle className="w-5 h-5" />
              Limitación de Responsabilidad
            </h2>
            <p className="text-gray-300 leading-relaxed">
              En la máxima medida permitida por la ley:
            </p>
            <div className="space-y-3 mt-4">
              <div className="bg-[#0f172a] rounded-lg p-4 border-l-4 border-yellow-500">
                <p className="text-gray-300 text-sm">
                  Genturix se proporciona "tal cual" y "según disponibilidad". No garantizamos que el servicio 
                  sea ininterrumpido, seguro o libre de errores.
                </p>
              </div>
              <div className="bg-[#0f172a] rounded-lg p-4 border-l-4 border-yellow-500">
                <p className="text-gray-300 text-sm">
                  No somos responsables de daños indirectos, incidentales, especiales, consecuentes o punitivos 
                  derivados del uso o imposibilidad de uso del servicio.
                </p>
              </div>
              <div className="bg-[#0f172a] rounded-lg p-4 border-l-4 border-yellow-500">
                <p className="text-gray-300 text-sm">
                  La responsabilidad total de Genturix no excederá el monto pagado por el servicio durante 
                  los 12 meses anteriores al evento que dio origen al reclamo.
                </p>
              </div>
            </div>
          </section>

          {/* Section 8: Contact Information */}
          <section className="bg-[#1e293b] rounded-xl p-6 space-y-4">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <span className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center text-blue-400">8</span>
              <Mail className="w-5 h-5" />
              Información de Contacto
            </h2>
            <p className="text-gray-300 leading-relaxed">
              Para preguntas sobre estos Términos de Servicio o cualquier aspecto del servicio, puede contactarnos:
            </p>
            <div className="bg-[#0f172a] rounded-lg p-4 space-y-2">
              <p className="text-gray-300">
                <strong className="text-white">Email:</strong> legal@genturix.com
              </p>
              <p className="text-gray-300">
                <strong className="text-white">Soporte:</strong> support@genturix.com
              </p>
              <p className="text-gray-300">
                <strong className="text-white">Sitio web:</strong> www.genturix.com
              </p>
            </div>
          </section>

          {/* Modifications Notice */}
          <section className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-6">
            <h3 className="font-semibold text-yellow-400 mb-2">Modificaciones a estos Términos</h3>
            <p className="text-gray-300 text-sm">
              Nos reservamos el derecho de modificar estos términos en cualquier momento. Los cambios entrarán 
              en vigor inmediatamente después de su publicación en la aplicación. El uso continuado del servicio 
              después de la publicación de cambios constituye su aceptación de los términos modificados.
            </p>
          </section>

          {/* Footer */}
          <footer className="text-center pt-8 border-t border-[#1e293b]">
            <p className="text-gray-500 text-sm">Genturix © 2026</p>
            <div className="flex justify-center gap-4 mt-4">
              <Link to="/privacy" className="text-blue-400 hover:text-blue-300 text-sm">
                Política de Privacidad
              </Link>
              <span className="text-gray-600">|</span>
              <Link to="/login" className="text-gray-400 hover:text-gray-300 text-sm">
                Iniciar Sesión
              </Link>
            </div>
          </footer>
        </div>
      </main>
    </div>
  );
};

export default TermsOfServicePage;
