cd ..
python train_model.py --gpu_ids 1 2 3 --batch_size 32 --imsize 8 --nlatentdim 32 --nepochs 300 --nepochs_pt2 500 --lrEnc 5E-5 --lrDec 5E-5 --lrEncD 5E-5 --lrDecD 5E-5 --encDRatio 1E-3 --decDRatio 1E-5 --model_name aaegan3Dv4-relu --save_dir ./test_aaegan/aaegan3Dv4_32D-relu_v3/ --train_module aaegan_trainv2 --noise=0.01 --imdir /root/results/ipp_dataset_cellnuc_seg_curated_7_24_17 --dataProvider DataProvider3Dh5 --saveStateIter 1 --saveProgressIter 1 --channels_pt1 0 2 5 --channels_pt2 0 1 2 5
