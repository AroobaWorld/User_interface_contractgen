import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Search, Upload, FileText, ShieldAlert, RefreshCw, LifeBuoy, ExternalLink } from "lucide-react";
import { motion } from "framer-motion";

export default function AIMZDashboard() {
  const [darkMode, setDarkMode] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [uploadMessage, setUploadMessage] = useState("");

  const exampleContracts = [
    { id: 1, name: "NDA Agreement", date: "2024-03-01", status: "Active" },
    { id: 2, name: "Supplier Contract", date: "2024-02-15", status: "Pending" },
    { id: 3, name: "Employment Agreement", date: "2024-01-10", status: "Expired" }
  ];

  const handleUpload = () => {
    setUploadMessage("File uploaded successfully!");
    setTimeout(() => setUploadMessage(""), 3000);
  };

  return (
    <div className={`min-h-screen p-8 transition-all duration-500 ${darkMode ? "bg-[#121826] text-white" : "bg-[#f4f7fc] text-gray-900"}`}>
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-6xl font-extrabold drop-shadow-md tracking-wide uppercase text-[#4A90E2] dark:text-[#A0C1E8]">AI-MZ Dashboard</h1>
          <Button 
            className="relative bg-[#4A90E2] text-white flex items-center px-8 py-3 rounded-full shadow-lg hover:shadow-xl transition-all"
            onClick={() => setDarkMode(!darkMode)}
          >
            <motion.span 
              initial={{ scale: 0.9 }} 
              animate={{ scale: 1 }} 
              transition={{ duration: 0.3 }}
            >
              {darkMode ? "Light Mode" : "Dark Mode"}
            </motion.span>
          </Button>
        </div>
        
        {/* Tabs for Navigation */}
        <Tabs defaultValue="repository">
          <TabsList className="flex space-x-4 bg-gray-300 dark:bg-gray-800 p-4 rounded-xl border border-gray-400 dark:border-gray-600">
            <TabsTrigger value="repository"><FileText size={20}/> Contract Repository</TabsTrigger>
            <TabsTrigger value="upload"><Upload size={20}/> Upload File</TabsTrigger>
            <TabsTrigger value="editor"><RefreshCw size={20}/> Contract Editor</TabsTrigger>
            <TabsTrigger value="risk"><ShieldAlert size={20}/> Risk Manager</TabsTrigger>
            <TabsTrigger value="lifecycle"><LifeBuoy size={20}/> Contract Lifecycle</TabsTrigger>
          </TabsList>
          
          <TabsContent value="editor">
            <Card className="shadow-lg rounded-xl bg-white dark:bg-gray-900 border border-gray-400 dark:border-gray-600 p-6">
              <CardContent>
                <h2 className="text-3xl font-bold mb-4 text-gray-900 dark:text-gray-100">Contract Editor</h2>
                <p className="text-lg text-gray-700 dark:text-gray-300">Edit your contracts in real-time using Microsoft Word Online or Google Docs.</p>
                <Button className="mt-4 bg-[#4A90E2] text-white px-6 py-3 rounded-full flex items-center space-x-2 hover:bg-[#357ABD]" onClick={() => window.open('https://docs.google.com', '_blank')}>
                  <ExternalLink size={20} /> <span>Open Editor</span>
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="risk">
            <Card className="shadow-lg rounded-xl bg-white dark:bg-gray-900 border border-gray-400 dark:border-gray-600 p-6">
              <CardContent>
                <h2 className="text-3xl font-bold mb-4 text-gray-900 dark:text-gray-100">Risk Manager</h2>
                <p className="text-lg text-gray-700 dark:text-gray-300">Visualize contract risks using real-time analytics and risk scoring.</p>
                <div className="h-40 bg-gray-200 dark:bg-gray-700 rounded-lg flex items-center justify-center text-gray-600 dark:text-gray-300">
                  📊 Risk Analysis Graph (Coming Soon)
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="lifecycle">
            <Card className="shadow-lg rounded-xl bg-white dark:bg-gray-900 border border-gray-400 dark:border-gray-600 p-6">
              <CardContent>
                <h2 className="text-3xl font-bold mb-4 text-gray-900 dark:text-gray-100">Contract Lifecycle</h2>
                <p className="text-lg text-gray-700 dark:text-gray-300">Track contract deadlines, approvals, and stakeholder responsibilities in a visual timeline.</p>
                <div className="h-40 bg-gray-200 dark:bg-gray-700 rounded-lg flex items-center justify-center text-gray-600 dark:text-gray-300">
                  ⏳ Interactive Timeline (Coming Soon)
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          <TabsContent value="repository">
            <Card className="shadow-lg rounded-xl bg-white dark:bg-gray-900 border border-gray-400 dark:border-gray-600 p-6">
              <CardContent>
                <h2 className="text-3xl font-bold mb-4 text-gray-900 dark:text-gray-100">Contract Repository</h2>
                <div className="flex space-x-2 mb-4">
                  <Input 
                    placeholder="Search contracts..." 
                    className="w-full bg-gray-100 dark:bg-gray-700 px-4 py-3 rounded-lg border border-gray-400 dark:border-gray-600"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                  <Button className="bg-[#4A90E2] text-white px-6 py-3 rounded-full hover:bg-[#357ABD]">Search</Button>
                </div>
                <ul className="mt-4 space-y-2">
                  {exampleContracts.filter(contract => contract.name.toLowerCase().includes(searchTerm.toLowerCase())).map(contract => (
                    <li key={contract.id} className="p-3 bg-gray-100 dark:bg-gray-800 rounded-lg flex justify-between border border-gray-400 dark:border-gray-600">
                      <span className="text-lg font-medium text-gray-900 dark:text-gray-200">{contract.name} - {contract.date}</span>
                      <span className={`text-lg font-semibold ${contract.status === "Active" ? "text-green-500" : contract.status === "Pending" ? "text-yellow-500" : "text-red-500"}`}>{contract.status}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="upload">
            <Card className="shadow-lg rounded-xl bg-white dark:bg-gray-900 border border-gray-400 dark:border-gray-600 p-6">
              <CardContent>
                <h2 className="text-3xl font-bold mb-4 text-gray-900 dark:text-gray-100">Upload a Contract</h2>
                <Input type="file" className="w-full bg-gray-100 dark:bg-gray-700 px-4 py-3 rounded-lg border border-gray-400 dark:border-gray-600"/>
                <Button onClick={handleUpload} className="mt-4 bg-[#4A90E2] text-white px-6 py-3 rounded-full hover:bg-[#357ABD]">Upload</Button>
                {uploadMessage && (
                  <motion.p 
                    initial={{ opacity: 0 }} 
                    animate={{ opacity: 1 }} 
                    exit={{ opacity: 0 }}
                    className="mt-2 text-green-500 text-lg font-medium"
                  >
                    {uploadMessage}
                  </motion.p>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
