cd ..
python train_model.py --gpu_ids 0 1 --batch_size 18 --imsize 3 --nlatentdim 128 --nepochs 250 --nepochs_pt2 500 --lrEnc 2E-4 --lrDec 2E-4 --lrEncD 2E-4 --lrDecD 2E-4 --encDRatio 1E-3 --decDRatio 1E-5 --model_name aaegan3D_resid --save_dir ./test_aaegan/aaegan3D_resid/ --train_module aaegan_trainv2 --noise=0.01 --imdir /root/data/release_4_1_17/results_v2/aligned_hdf5 --dataProvider DataProvider3D --saveStateIter 1
