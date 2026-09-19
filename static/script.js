const fileInput =
    document.getElementById("fileInput");

const fileName =
    document.getElementById("fileName");

const processButton =
    document.getElementById("processButton");

const resultSection =
    document.getElementById("resultSection");

const documentText =
    document.getElementById("documentText");

const resultText =
    document.getElementById("resultText");

const finalResultSection =
    document.getElementById("finalResultSection");

const finalResultTitle =
    document.getElementById("finalResultTitle");

const characterCount =
    document.getElementById("characterCount");

const detectedLanguage =
    document.getElementById("detectedLanguage");

const documentType =
    document.getElementById("documentType");

const errorMessage =
    document.getElementById("errorMessage");

const statusMessage =
    document.getElementById("statusMessage");


let selectedFile = null;
let extractedText = "";
let uploadedDocumentType = "unknown";


// =========================================================
// FILE SELECTION
// =========================================================

fileInput.addEventListener(
    "change",
    () => {

        if (!fileInput.files.length) {

            selectedFile = null;

            processButton.disabled = true;

            fileName.textContent = "";

            return;
        }


        selectedFile =
            fileInput.files[0];


        fileName.textContent =
            `Selected: ${selectedFile.name}`;


        processButton.disabled = false;
    }
);


// =========================================================
// MAIN PROCESS
// =========================================================

processButton.addEventListener(
    "click",
    async () => {

        if (!selectedFile) {
            return;
        }


        const targetLanguage =
            document.querySelector(
                'input[name="targetLanguage"]:checked'
            ).value;


        const task =
            document.querySelector(
                'input[name="task"]:checked'
            ).value;


        processButton.disabled = true;

        processButton.textContent =
            "Processing...";


        resultSection.classList.add(
            "hidden"
        );

        finalResultSection.classList.add(
            "hidden"
        );

        errorMessage.classList.add(
            "hidden"
        );


        try {

            // =================================================
            // UPLOAD + OCR / EXTRACTION
            // =================================================

            statusMessage.textContent =
                "Reading your document...";


            const formData =
                new FormData();


            formData.append(
                "file",
                selectedFile
            );


            const uploadResponse =
                await fetch(
                    "/upload",
                    {
                        method: "POST",
                        body: formData
                    }
                );


            const uploadData =
                await uploadResponse.json();


            if (
                !uploadResponse.ok ||
                !uploadData.success
            ) {

                throw new Error(
                    uploadData.error ||
                    "Could not read the document."
                );
            }


            extractedText =
                uploadData.text || "";


            uploadedDocumentType =
                uploadData.document_type ||
                "unknown";


            documentText.textContent =
                extractedText;


            characterCount.textContent =
                `${uploadData.characters.toLocaleString()} characters`;


            detectedLanguage.textContent =
                formatLanguage(
                    uploadData.detected_language
                );


            documentType.textContent =
                uploadData.document_label ||
                "Legal Document";


            resultSection.classList.remove(
                "hidden"
            );


            // =================================================
            // PROCESS SELECTED TASK
            // =================================================

            statusMessage.textContent =
                `${getTaskTitle(task)} in ${targetLanguage}...`;


            const processResponse =
                await fetch(
                    "/process",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({

                            text:
                                extractedText,

                            target_language:
                                targetLanguage,

                            task:
                                task,

                            document_type:
                                uploadedDocumentType
                        })
                    }
                );


            const processData =
                await processResponse.json();


            if (
                !processResponse.ok ||
                !processData.success
            ) {

                throw new Error(
                    processData.error ||
                    "Could not process the document."
                );
            }


            resultText.textContent =
                processData.result;


            finalResultTitle.textContent =
                getTaskTitle(task);


            finalResultSection.classList.remove(
                "hidden"
            );


            statusMessage.textContent =
                `${getTaskTitle(task)} completed in ${targetLanguage}.`;


            finalResultSection.scrollIntoView({
                behavior: "smooth"
            });


        } catch (error) {

            errorMessage.textContent =
                error.message;

            errorMessage.classList.remove(
                "hidden"
            );

            resultSection.classList.remove(
                "hidden"
            );


        } finally {

            processButton.disabled = false;

            processButton.textContent =
                "Process Document";
        }
    }
);


// =========================================================
// TASK TITLES
// =========================================================

function getTaskTitle(task) {

    const titles = {

        translate:
            "Translated Document",

        summarize:
            "Document Summary",

        key_information:
            "Key Information",

        simplify:
            "Simplified Document",

        legal_analysis:
            "Legal Analysis"
    };


    return titles[task] || "Result";
}


// =========================================================
// LANGUAGE
// =========================================================

function formatLanguage(language) {

    if (!language) {
        return "Unknown";
    }


    const value =
        language.toLowerCase();


    if (value.includes("marathi")) {
        return "Marathi";
    }


    if (value.includes("english")) {
        return "English";
    }


    return language;
}
