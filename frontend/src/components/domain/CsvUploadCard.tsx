import { useEffect, useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useQueryClient } from '@tanstack/react-query';
import { AlertCircle, CheckCircle2, Upload } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { queryKeys } from '../../api/queryKeys';
import { useJobStatus } from '../../hooks/usePromiseDetail';
import { useUploadCredits } from '../../hooks/useSyncAndCredits';

const REQUIRED_CSV_COLUMNS = ['date', 'description', 'amount', 'reference_number'] as const;

const csvFormSchema = z.object({
  bank_name: z.string().min(1, 'Bank name is required').max(50),
  account_last4: z
    .string()
    .regex(/^(\d{4})?$/, 'Enter exactly 4 digits')
    .optional(),
});

type CsvFormValues = z.infer<typeof csvFormSchema>;

async function readFileText(file: File): Promise<string> {
  if (typeof file.text === 'function') {
    return file.text();
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(typeof reader.result === 'string' ? reader.result : '');
    reader.onerror = () => reject(reader.error ?? new Error('Failed to read file'));
    reader.readAsText(file);
  });
}

export async function validateCsvHeaders(file: File): Promise<string[]> {
  const text = await readFileText(file);
  const firstLine = text.replace(/^\uFEFF/, '').split(/\r?\n/)[0] ?? '';
  const headers = firstLine
    .split(',')
    .map((h) => h.trim().replace(/^"|"$/g, '').toLowerCase())
    .filter(Boolean);
  return REQUIRED_CSV_COLUMNS.filter((col) => !headers.includes(col));
}

export function CsvUploadCard() {
  const queryClient = useQueryClient();
  const uploadMutation = useUploadCredits();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [clientError, setClientError] = useState<string | null>(null);
  const [uploadJobId, setUploadJobId] = useState<string | null>(null);

  const jobQuery = useJobStatus(uploadJobId);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CsvFormValues>({
    resolver: zodResolver(csvFormSchema),
    defaultValues: { bank_name: 'HDFC', account_last4: '' },
  });

  useEffect(() => {
    if (jobQuery.data?.status === 'completed') {
      void queryClient.invalidateQueries({ queryKey: ['promises'] });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.credits() });
    }
  }, [jobQuery.data?.status, queryClient]);

  const onSubmit = async (values: CsvFormValues) => {
    setClientError(null);
    if (!selectedFile) {
      setClientError('Please select a CSV file.');
      return;
    }
    if (!selectedFile.name.toLowerCase().endsWith('.csv')) {
      setClientError('File must have a .csv extension.');
      return;
    }
    if (selectedFile.size > 10 * 1024 * 1024) {
      setClientError('CSV file must be 10 MB or smaller.');
      return;
    }

    const missingCols = await validateCsvHeaders(selectedFile);
    if (missingCols.length > 0) {
      setClientError(`CSV is missing required column(s): ${missingCols.join(', ')}`);
      return;
    }

    const res = await uploadMutation.mutateAsync({
      file: selectedFile,
      bank_name: values.bank_name,
      account_last4: values.account_last4 || undefined,
    });
    setUploadJobId(res.job_id);
  };

  return (
    <section
      aria-label="Bank Credit CSV Upload"
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <h2 className="text-base font-semibold text-slate-900">Upload Bank Statement (CSV)</h2>
      <p className="mt-1 text-xs text-slate-500">
        Required columns: <code>date</code>, <code>description</code>, <code>amount</code>,{' '}
        <code>reference_number</code>.
      </p>

      <form onSubmit={handleSubmit(onSubmit)} className="mt-4 space-y-3" noValidate>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <label className="block text-xs font-medium text-slate-700">
            Bank Name
            <input
              type="text"
              {...register('bank_name')}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            {errors.bank_name && (
              <span className="mt-1 block text-xs text-red-600">{errors.bank_name.message}</span>
            )}
          </label>

          <label className="block text-xs font-medium text-slate-700">
            Account Last 4 (Optional)
            <input
              type="text"
              maxLength={4}
              placeholder="1234"
              {...register('account_last4')}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            {errors.account_last4 && (
              <span className="mt-1 block text-xs text-red-600">
                {errors.account_last4.message}
              </span>
            )}
          </label>

          <label className="block text-xs font-medium text-slate-700">
            CSV File
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => {
                setSelectedFile(e.target.files?.[0] ?? null);
                setClientError(null);
              }}
              className="mt-1 block w-full text-xs text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-brand-50 file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-brand-700"
            />
          </label>
        </div>

        {(clientError || uploadMutation.isError) && (
          <div
            role="alert"
            className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700"
          >
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{clientError ?? uploadMutation.error?.userMessage}</span>
          </div>
        )}

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={uploadMutation.isPending}
            className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
          >
            <Upload className="h-3.5 w-3.5" />
            {uploadMutation.isPending ? 'Uploading...' : 'Upload & Match Credits'}
          </button>

          {uploadJobId && jobQuery.data && (
            <span className="inline-flex items-center gap-1.5 text-xs text-slate-600">
              {jobQuery.data.status === 'completed' && (
                <CheckCircle2 className="h-4 w-4 text-green-600" />
              )}
              Job {jobQuery.data.status} ({jobQuery.data.progress_pct ?? 0}%)
            </span>
          )}
        </div>
      </form>
    </section>
  );
}
