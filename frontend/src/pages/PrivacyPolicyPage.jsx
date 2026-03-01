import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Shield, Mail, Lock, Bell, Database, Clock, Users } from 'lucide-react';

const PrivacyPolicyPage = () => {
  useEffect(() => {
    document.title = 'Privacy Policy | Genturix';
    // Add meta description
    const metaDescription = document.querySelector('meta[name="description"]');
    if (metaDescription) {
      metaDescription.setAttribute('content', 'Genturix Privacy Policy - Learn how we collect, use, and protect your personal information in our condominium security platform.');
    }
    // Scroll to top on mount
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="h-screen flex flex-col bg-[#0f172a] text-gray-200">
      {/* Header - Fixed at top */}
      <header className="flex-shrink-0 bg-[#0f172a] border-b border-[#1e293b]">
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

      {/* Content - Scrollable area */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-8 pb-20">
        <div className="space-y-8">
          {/* Title */}
          <div className="text-center space-y-2">
            <Shield className="w-12 h-12 mx-auto text-blue-400" />
            <h1 className="text-3xl font-bold text-white">Política de Privacidad</h1>
            <p className="text-gray-400">Última actualización: Marzo 2026</p>
          </div>

          {/* Section 1: Introduction */}
          <section className="bg-[#1e293b] rounded-xl p-6 space-y-4">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <span className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center text-blue-400">1</span>
              Introducción
            </h2>
            <p className="text-gray-300 leading-relaxed">
              Bienvenido a Genturix. Nos comprometemos a proteger su privacidad y garantizar la seguridad de su información personal. 
              Esta Política de Privacidad explica cómo recopilamos, usamos, almacenamos y protegemos sus datos cuando utiliza 
              nuestra plataforma de gestión de seguridad para condominios.
            </p>
            <p className="text-gray-300 leading-relaxed">
              Al utilizar Genturix, usted acepta las prácticas descritas en esta política. Si no está de acuerdo con alguna 
              parte de esta política, le recomendamos no utilizar nuestros servicios.
            </p>
          </section>

          {/* Section 2: Data We Collect */}
          <section className="bg-[#1e293b] rounded-xl p-6 space-y-4">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <span className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center text-blue-400">2</span>
              <Database className="w-5 h-5" />
              Datos que Recopilamos
            </h2>
            <div className="space-y-3">
              <div className="bg-[#0f172a] rounded-lg p-4">
                <h3 className="font-medium text-white mb-2">Información de Cuenta</h3>
                <ul className="text-gray-300 text-sm space-y-1 list-disc list-inside">
                  <li>Nombre completo</li>
                  <li>Dirección de correo electrónico</li>
                  <li>Número de teléfono</li>
                  <li>Número de apartamento/unidad</li>
                  <li>Rol dentro del condominio (residente, guardia, administrador)</li>
                </ul>
              </div>
              <div className="bg-[#0f172a] rounded-lg p-4">
                <h3 className="font-medium text-white mb-2">Datos de Visitantes</h3>
                <ul className="text-gray-300 text-sm space-y-1 list-disc list-inside">
                  <li>Nombre del visitante</li>
                  <li>Documento de identidad (opcional)</li>
                  <li>Placa del vehículo (opcional)</li>
                  <li>Fecha y hora de entrada/salida</li>
                  <li>Propósito de la visita</li>
                </ul>
              </div>
              <div className="bg-[#0f172a] rounded-lg p-4">
                <h3 className="font-medium text-white mb-2">Datos Técnicos</h3>
                <ul className="text-gray-300 text-sm space-y-1 list-disc list-inside">
                  <li>Dirección IP</li>
                  <li>Tipo de dispositivo y navegador</li>
                  <li>Configuración de notificaciones push</li>
                  <li>Registros de acceso y actividad</li>
                </ul>
              </div>
            </div>
          </section>

          {/* Section 3: How We Use Data */}
          <section className="bg-[#1e293b] rounded-xl p-6 space-y-4">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <span className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center text-blue-400">3</span>
              Cómo Usamos sus Datos
            </h2>
            <p className="text-gray-300 leading-relaxed">
              Utilizamos su información para los siguientes propósitos:
            </p>
            <ul className="text-gray-300 space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">•</span>
                <span><strong>Gestión de accesos:</strong> Control de entrada y salida de visitantes autorizados.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">•</span>
                <span><strong>Seguridad:</strong> Alertas de pánico y comunicación con personal de seguridad.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">•</span>
                <span><strong>Reservaciones:</strong> Gestión de áreas comunes del condominio.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">•</span>
                <span><strong>Comunicación:</strong> Envío de notificaciones sobre visitantes y alertas.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">•</span>
                <span><strong>Auditoría:</strong> Registro de eventos para transparencia y seguridad.</span>
              </li>
            </ul>
          </section>

          {/* Section 4: Push Notifications */}
          <section className="bg-[#1e293b] rounded-xl p-6 space-y-4">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <span className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center text-blue-400">4</span>
              <Bell className="w-5 h-5" />
              Notificaciones Push
            </h2>
            <p className="text-gray-300 leading-relaxed">
              Genturix utiliza notificaciones push para alertarle sobre:
            </p>
            <ul className="text-gray-300 space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-green-400 mt-1">✓</span>
                <span>Llegada de visitantes autorizados</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-400 mt-1">✓</span>
                <span>Alertas de emergencia y pánico</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-400 mt-1">✓</span>
                <span>Confirmación de reservaciones</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-400 mt-1">✓</span>
                <span>Actualizaciones importantes del condominio</span>
              </li>
            </ul>
            <p className="text-gray-400 text-sm mt-4">
              Puede desactivar las notificaciones push en cualquier momento desde la configuración de su dispositivo 
              o dentro de la aplicación.
            </p>
          </section>

          {/* Section 5: Security */}
          <section className="bg-[#1e293b] rounded-xl p-6 space-y-4">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <span className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center text-blue-400">5</span>
              <Lock className="w-5 h-5" />
              Seguridad de Datos
            </h2>
            <p className="text-gray-300 leading-relaxed">
              Implementamos medidas de seguridad técnicas y organizativas para proteger sus datos:
            </p>
            <ul className="text-gray-300 space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">•</span>
                <span>Encriptación de datos en tránsito (HTTPS/TLS)</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">•</span>
                <span>Contraseñas hasheadas con algoritmos seguros (bcrypt)</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">•</span>
                <span>Tokens de autenticación con expiración automática</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">•</span>
                <span>Aislamiento de datos entre condominios (multi-tenant)</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">•</span>
                <span>Registro de auditoría de todas las acciones sensibles</span>
              </li>
            </ul>
          </section>

          {/* Section 6: Third Party Services */}
          <section className="bg-[#1e293b] rounded-xl p-6 space-y-4">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <span className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center text-blue-400">6</span>
              <Users className="w-5 h-5" />
              Servicios de Terceros
            </h2>
            <p className="text-gray-300 leading-relaxed">
              Utilizamos los siguientes servicios de terceros que pueden procesar sus datos:
            </p>
            <div className="grid gap-3 mt-4">
              <div className="bg-[#0f172a] rounded-lg p-4 flex items-center gap-4">
                <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
                  <Mail className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <h4 className="font-medium text-white">Resend</h4>
                  <p className="text-gray-400 text-sm">Envío de correos electrónicos transaccionales</p>
                </div>
              </div>
              <div className="bg-[#0f172a] rounded-lg p-4 flex items-center gap-4">
                <div className="w-10 h-10 bg-green-500/20 rounded-lg flex items-center justify-center">
                  <Bell className="w-5 h-5 text-green-400" />
                </div>
                <div>
                  <h4 className="font-medium text-white">Web Push (VAPID)</h4>
                  <p className="text-gray-400 text-sm">Notificaciones push en tiempo real</p>
                </div>
              </div>
            </div>
          </section>

          {/* Section 7: Data Retention */}
          <section className="bg-[#1e293b] rounded-xl p-6 space-y-4">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <span className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center text-blue-400">7</span>
              <Clock className="w-5 h-5" />
              Retención de Datos
            </h2>
            <p className="text-gray-300 leading-relaxed">
              Conservamos sus datos durante el tiempo que sea necesario para proporcionar nuestros servicios:
            </p>
            <ul className="text-gray-300 space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">•</span>
                <span><strong>Datos de cuenta:</strong> Mientras mantenga su cuenta activa</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">•</span>
                <span><strong>Registros de visitas:</strong> 2 años para propósitos de auditoría</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-1">•</span>
                <span><strong>Logs de seguridad:</strong> 1 año para análisis de incidentes</span>
              </li>
            </ul>
            <p className="text-gray-400 text-sm mt-4">
              Puede solicitar la eliminación de sus datos contactándonos. Los datos se eliminarán 
              dentro de los 30 días siguientes a la solicitud, excepto cuando existan obligaciones legales de retención.
            </p>
          </section>

          {/* Section 8: Contact */}
          <section className="bg-[#1e293b] rounded-xl p-6 space-y-4">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <span className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center text-blue-400">8</span>
              <Mail className="w-5 h-5" />
              Contacto
            </h2>
            <p className="text-gray-300 leading-relaxed">
              Si tiene preguntas sobre esta Política de Privacidad o desea ejercer sus derechos sobre sus datos personales, 
              puede contactarnos:
            </p>
            <div className="bg-[#0f172a] rounded-lg p-4 space-y-2">
              <p className="text-gray-300">
                <strong className="text-white">Email:</strong> privacy@genturix.com
              </p>
              <p className="text-gray-300">
                <strong className="text-white">Sitio web:</strong> www.genturix.com
              </p>
            </div>
          </section>

          {/* Footer */}
          <footer className="text-center pt-8 border-t border-[#1e293b]">
            <p className="text-gray-500 text-sm">Genturix © 2026</p>
            <div className="flex justify-center gap-4 mt-4">
              <Link to="/terms" className="text-blue-400 hover:text-blue-300 text-sm">
                Términos de Servicio
              </Link>
              <span className="text-gray-600">|</span>
              <Link to="/login" className="text-gray-400 hover:text-gray-300 text-sm">
                Iniciar Sesión
              </Link>
            </div>
          </footer>
        </div>
        </div>
      </main>
    </div>
  );
};

export default PrivacyPolicyPage;
